import hashlib
import hmac
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order, OrderItem, TimeSlot
from apps.payments.models import Payment
from apps.payments.services import process_mercado_pago_payment, validate_webhook_signature


class MercadoPagoApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer@example.com', 'SecurePass123!')
        category = Category.objects.create(name='Cakes', slug='cakes')
        product = Product.objects.create(
            category=category,
            name='Chocolate Cake',
            slug='chocolate-cake',
            description='Chocolate cake',
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            size='Medium',
            sku='CAKE-MEDIUM',
            price=5500,
            stock=3,
        )
        slot = TimeSlot.objects.get(name='09:00-12:00')
        self.order = Order.objects.create(
            customer=self.user,
            delivery_method=Order.DeliveryMethod.PICKUP,
            scheduled_date=timezone.localdate() + timedelta(days=1),
            time_slot=slot,
            subtotal=11000,
            total=11000,
            payment_expires_at=timezone.now() + timedelta(minutes=15),
        )
        OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name=product.name,
            variant_size=self.variant.size,
            unit_price=5500,
            quantity=2,
            subtotal=11000,
        )
        self.client.force_authenticate(self.user)

    @patch('apps.payments.services.MercadoPagoClient')
    def test_customer_creates_a_preference_for_own_reserved_order(self, client_class):
        client_class.return_value.create_preference.return_value = {
            'id': 'preference-123',
            'init_point': 'https://checkout.example/preference-123',
        }

        response = self.client.post(reverse('payment-preference', kwargs={'code': self.order.code}))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get()
        self.assertEqual(payment.preference_id, 'preference-123')
        self.assertEqual(payment.amount, 11000)
        self.assertEqual(response.data['checkout_url'], 'https://checkout.example/preference-123')

    @patch('apps.payments.services.MercadoPagoClient')
    def test_approved_webhook_marks_order_as_paid_idempotently(self, client_class):
        Payment.objects.create(
            order=self.order,
            amount=11000,
            currency='PEN',
            preference_id='preference-123',
            checkout_url='https://checkout.example/preference-123',
        )
        client_class.return_value.get_payment.return_value = {
            'id': 'payment-123',
            'preference_id': 'preference-123',
            'external_reference': str(self.order.code),
            'transaction_amount': 110.0,
            'currency_id': 'PEN',
            'status': 'approved',
        }

        response = self.client.post(reverse('mercado-pago-webhook'), {'data': {'id': 'payment-123'}}, format='json')
        repeated = self.client.post(reverse('mercado-pago-webhook'), {'data': {'id': 'payment-123'}}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(repeated.status_code, status.HTTP_204_NO_CONTENT)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(Payment.objects.get().status, Payment.Status.APPROVED)

    @patch('apps.payments.services.MercadoPagoClient')
    def test_rejected_payment_restores_reserved_stock(self, client_class):
        self.variant.stock = 1
        self.variant.save(update_fields=['stock'])
        Payment.objects.create(
            order=self.order,
            amount=11000,
            currency='PEN',
            preference_id='preference-123',
            checkout_url='https://checkout.example/preference-123',
        )
        client_class.return_value.get_payment.return_value = {
            'id': 'payment-123',
            'preference_id': 'preference-123',
            'external_reference': str(self.order.code),
            'transaction_amount': 110.0,
            'currency_id': 'PEN',
            'status': 'rejected',
        }

        process_mercado_pago_payment('payment-123')

        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertTrue(self.order.stock_released)
        self.assertEqual(self.variant.stock, 3)

    @override_settings(MERCADO_PAGO_WEBHOOK_SECRET='secret')
    def test_webhook_signature_is_validated(self):
        manifest = 'id:payment-123;request-id:request-123;ts:1700000000;'
        digest = hmac.new(b'secret', manifest.encode('utf-8'), hashlib.sha256).hexdigest()

        self.assertTrue(
            validate_webhook_signature(
                signature=f'ts=1700000000,v1={digest}',
                request_id='request-123',
                payment_id='payment-123',
            )
        )
        self.assertFalse(
            validate_webhook_signature(
                signature='ts=1700000000,v1=invalid',
                request_id='request-123',
                payment_id='payment-123',
            )
        )
