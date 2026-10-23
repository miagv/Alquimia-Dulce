from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Address
from apps.orders.models import BusinessSettings, Order, OrderItem, TimeSlot
from apps.orders.services import PAYMENT_RESERVATION_MINUTES, validate_schedule

from .models import CustomOrderQuote, CustomOrderRequest


def create_custom_order_request(*, user, delivery_method, scheduled_date, time_slot_id, address_id=None, **details):
    with transaction.atomic():
        settings = BusinessSettings.objects.select_for_update().get(pk=1)
        time_slot = TimeSlot.objects.filter(pk=time_slot_id, is_active=True).first()
        if not time_slot:
            raise ValidationError('The selected time slot is not available.')
        validate_schedule(scheduled_date, time_slot, settings)

        address = None
        delivery_fee = 0
        if delivery_method == CustomOrderRequest.DeliveryMethod.DELIVERY:
            address = Address.objects.filter(pk=address_id, user=user).first()
            if not address:
                raise ValidationError('A valid delivery address is required.')
            delivery_fee = settings.delivery_fee

        return CustomOrderRequest.objects.create(
            customer=user,
            delivery_method=delivery_method,
            delivery_address=address,
            delivery_district=address.district if address else '',
            delivery_address_line=address.address_line if address else '',
            delivery_reference=address.reference if address else '',
            delivery_fee=delivery_fee,
            scheduled_date=scheduled_date,
            time_slot=time_slot,
            **details,
        )


def quote_custom_order(*, request_id, total, scheduled_date, time_slot_id, notes, expires_at):
    with transaction.atomic():
        custom_request = CustomOrderRequest.objects.select_for_update().get(pk=request_id)
        if custom_request.status not in {
            CustomOrderRequest.Status.SUBMITTED,
            CustomOrderRequest.Status.QUOTED,
        }:
            raise ValidationError('This request cannot be quoted.')
        if expires_at <= timezone.now():
            raise ValidationError('The quote expiration must be in the future.')
        if total <= custom_request.delivery_fee:
            raise ValidationError('The quote total must exceed the delivery fee.')

        settings = BusinessSettings.objects.get(pk=1)
        time_slot = TimeSlot.objects.filter(pk=time_slot_id, is_active=True).first()
        if not time_slot:
            raise ValidationError('The selected time slot is not available.')
        validate_schedule(scheduled_date, time_slot, settings)

        quote, _ = CustomOrderQuote.objects.update_or_create(
            request=custom_request,
            defaults={
                'total': total,
                'delivery_fee': custom_request.delivery_fee,
                'scheduled_date': scheduled_date,
                'time_slot': time_slot,
                'notes': notes,
                'expires_at': expires_at,
            },
        )
        custom_request.status = CustomOrderRequest.Status.QUOTED
        custom_request.save(update_fields=['status', 'updated_at'])
        return quote


def reject_custom_order(*, request_id):
    with transaction.atomic():
        custom_request = CustomOrderRequest.objects.select_for_update().get(pk=request_id)
        if custom_request.status not in {
            CustomOrderRequest.Status.SUBMITTED,
            CustomOrderRequest.Status.QUOTED,
        }:
            raise ValidationError('This request cannot be rejected.')
        custom_request.status = CustomOrderRequest.Status.REJECTED
        custom_request.save(update_fields=['status', 'updated_at'])
        return custom_request


def accept_custom_order_quote(*, request_id, user):
    with transaction.atomic():
        custom_request = CustomOrderRequest.objects.select_for_update().filter(
            pk=request_id,
            customer=user,
        ).first()
        if not custom_request:
            raise ValidationError('Custom order request was not found.')
        if custom_request.status != CustomOrderRequest.Status.QUOTED:
            raise ValidationError('This request is not awaiting quote acceptance.')

        quote = CustomOrderQuote.objects.select_for_update().select_related('time_slot').filter(
            request=custom_request
        ).first()
        if not quote or quote.expires_at <= timezone.now():
            custom_request.status = CustomOrderRequest.Status.EXPIRED
            custom_request.save(update_fields=['status', 'updated_at'])
            raise ValidationError('The quote has expired.')
        if quote.order_id:
            raise ValidationError('This quote has already been accepted.')

        settings = BusinessSettings.objects.select_for_update().get(pk=1)
        time_slot = TimeSlot.objects.select_for_update().filter(pk=quote.time_slot_id, is_active=True).first()
        if not time_slot:
            raise ValidationError('The selected time slot is not available.')
        validate_schedule(quote.scheduled_date, time_slot, settings)

        order = Order.objects.create(
            customer=user,
            delivery_method=custom_request.delivery_method,
            scheduled_date=quote.scheduled_date,
            time_slot=time_slot,
            delivery_address=custom_request.delivery_address,
            delivery_district=custom_request.delivery_district,
            delivery_address_line=custom_request.delivery_address_line,
            delivery_reference=custom_request.delivery_reference,
            subtotal=quote.total - quote.delivery_fee,
            delivery_fee=quote.delivery_fee,
            total=quote.total,
            notes=quote.notes,
            payment_expires_at=timezone.now() + timedelta(minutes=PAYMENT_RESERVATION_MINUTES),
        )
        OrderItem.objects.create(
            order=order,
            product_name='Custom order',
            variant_size=f'{custom_request.servings} servings',
            unit_price=quote.total - quote.delivery_fee,
            quantity=1,
            subtotal=quote.total - quote.delivery_fee,
        )
        quote.order = order
        quote.accepted_at = timezone.now()
        quote.save(update_fields=['order', 'accepted_at', 'updated_at'])
        custom_request.status = CustomOrderRequest.Status.APPROVED
        custom_request.save(update_fields=['status', 'updated_at'])
        return order
