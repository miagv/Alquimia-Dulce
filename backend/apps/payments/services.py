import hashlib
import hmac
import json
from datetime import timezone as datetime_timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services import cancel_order_and_restore_stock

from .models import Payment


MERCADO_PAGO_API_URL = 'https://api.mercadopago.com'


class MercadoPagoConfigurationError(Exception):
    pass


class MercadoPagoApiError(Exception):
    pass


class MercadoPagoClient:
    def __init__(self, access_token=None):
        self.access_token = access_token or settings.MERCADO_PAGO_ACCESS_TOKEN
        if not self.access_token:
            raise MercadoPagoConfigurationError('MERCADO_PAGO_ACCESS_TOKEN is not configured.')

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(
            f'{MERCADO_PAGO_API_URL}{path}',
            data=data,
            method=method,
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            body = error.read().decode('utf-8')
            raise MercadoPagoApiError(f'Mercado Pago returned {error.code}: {body}') from error
        except URLError as error:
            raise MercadoPagoApiError('Could not reach Mercado Pago.') from error

    def create_preference(self, payload):
        return self._request('POST', '/checkout/preferences', payload)

    def get_payment(self, payment_id):
        return self._request('GET', f'/v1/payments/{payment_id}')


def cents_to_amount(cents):
    return str((Decimal(cents) / Decimal(100)).quantize(Decimal('0.01')))


def amount_to_cents(amount):
    return int((Decimal(str(amount)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def create_payment_preference(*, order_code, user):
    with transaction.atomic():
        order = Order.objects.select_for_update().prefetch_related('items').filter(
            code=order_code,
            customer=user,
        ).first()
        if not order:
            raise ValidationError('Order was not found.')
        if order.status != Order.Status.PENDING_PAYMENT:
            raise ValidationError('This order is not awaiting payment.')
        if not order.payment_expires_at or order.payment_expires_at <= timezone.now():
            cancel_order_and_restore_stock(order)
            raise ValidationError('The payment reservation has expired.')

        payment = Payment.objects.select_for_update().filter(
            order=order,
            provider=Payment.Provider.MERCADO_PAGO,
            status=Payment.Status.PENDING,
        ).first()
        if payment and payment.preference_id and payment.checkout_url:
            return payment
        if not payment:
            payment = Payment.objects.create(order=order, amount=order.total, currency='PEN')

        payload = {
            'items': [
                {
                    'title': f'{item.product_name} - {item.variant_size}',
                    'quantity': item.quantity,
                    'currency_id': 'PEN',
                    'unit_price': float(cents_to_amount(item.unit_price)),
                }
                for item in order.items.all()
            ],
            'external_reference': str(order.code),
            'expires': True,
            'expiration_date_to': order.payment_expires_at.astimezone(datetime_timezone.utc).isoformat(),
        }
        back_urls = {
            'success': settings.MERCADO_PAGO_SUCCESS_URL,
            'failure': settings.MERCADO_PAGO_FAILURE_URL,
            'pending': settings.MERCADO_PAGO_PENDING_URL,
        }
        if any(back_urls.values()):
            payload['back_urls'] = {key: value for key, value in back_urls.items() if value}
        if settings.MERCADO_PAGO_NOTIFICATION_URL:
            payload['notification_url'] = settings.MERCADO_PAGO_NOTIFICATION_URL

        preference = MercadoPagoClient().create_preference(payload)
        checkout_url = preference.get('init_point') or preference.get('sandbox_init_point')
        if not preference.get('id') or not checkout_url:
            raise MercadoPagoApiError('Mercado Pago returned an incomplete preference.')

        payment.preference_id = preference['id']
        payment.checkout_url = checkout_url
        payment.provider_response = preference
        payment.save(update_fields=['preference_id', 'checkout_url', 'provider_response', 'updated_at'])
        return payment


def validate_webhook_signature(*, signature, request_id, payment_id):
    secret = settings.MERCADO_PAGO_WEBHOOK_SECRET
    if not secret:
        return True
    if not signature or not request_id:
        return False

    parts = {}
    for item in signature.split(','):
        key, separator, value = item.strip().partition('=')
        if separator:
            parts[key] = value
    timestamp = parts.get('ts')
    received_hash = parts.get('v1')
    if not timestamp or not received_hash:
        return False

    manifest = f'id:{payment_id};request-id:{request_id};ts:{timestamp};'
    expected_hash = hmac.new(
        secret.encode('utf-8'), manifest.encode('utf-8'), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_hash, received_hash)


def process_mercado_pago_payment(payment_id):
    payment_data = MercadoPagoClient().get_payment(payment_id)
    external_reference = payment_data.get('external_reference')
    preference_id = payment_data.get('preference_id')
    if not external_reference or not preference_id:
        raise ValidationError('Mercado Pago payment is missing order references.')

    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related('order').filter(
            preference_id=preference_id,
            order__code=external_reference,
        ).first()
        if not payment:
            raise ValidationError('No matching payment preference was found.')

        order = Order.objects.select_for_update().get(pk=payment.order_id)
        if payment.amount != amount_to_cents(payment_data.get('transaction_amount', 0)):
            raise ValidationError('Mercado Pago amount does not match the order total.')
        if payment.currency != payment_data.get('currency_id'):
            raise ValidationError('Mercado Pago currency does not match the order currency.')

        provider_status = payment_data.get('status')
        status_map = {
            'approved': Payment.Status.APPROVED,
            'rejected': Payment.Status.REJECTED,
            'cancelled': Payment.Status.CANCELLED,
            'refunded': Payment.Status.REFUNDED,
        }
        payment.status = status_map.get(provider_status, Payment.Status.PENDING)
        payment.external_payment_id = str(payment_data['id'])
        payment.provider_response = payment_data
        payment.save(
            update_fields=['status', 'external_payment_id', 'provider_response', 'updated_at']
        )

        if payment.status == Payment.Status.APPROVED:
            # A late approval is recorded but never revives an expired reservation.
            if order.status == Order.Status.PENDING_PAYMENT and order.payment_expires_at > timezone.now():
                order.status = Order.Status.PAID
                order.save(update_fields=['status', 'updated_at'])
        elif payment.status in {Payment.Status.REJECTED, Payment.Status.CANCELLED}:
            if order.status == Order.Status.PENDING_PAYMENT:
                cancel_order_and_restore_stock(order)

        return payment
