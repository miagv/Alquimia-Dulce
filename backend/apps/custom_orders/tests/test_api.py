from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Address, User
from apps.custom_orders.models import CustomOrderRequest
from apps.orders.models import Order, TimeSlot
from apps.payments.models import Payment


class CustomOrderApiTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer@example.com', 'SecurePass123!')
        self.admin = User.objects.create_user(
            'admin@example.com',
            'SecurePass123!',
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            recipient_name='Customer',
            recipient_phone='999888777',
            district='Lima',
            address_line='Central avenue 123',
        )
        self.slot = TimeSlot.objects.get(name='12:00-15:00')
        self.scheduled_date = timezone.localdate() + timedelta(days=2)

    def create_request(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse('custom-order-list'),
            {
                'delivery_method': CustomOrderRequest.DeliveryMethod.DELIVERY,
                'address_id': self.address.id,
                'scheduled_date': self.scheduled_date.isoformat(),
                'time_slot_id': self.slot.id,
                'servings': 20,
                'flavor': 'Chocolate',
                'theme': 'Birthday',
                'message': 'Happy birthday',
                'description': 'Pastel con decoracion floral',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return CustomOrderRequest.objects.get()

    def quote_request(self, custom_request):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse('admin-custom-order-quote', kwargs={'pk': custom_request.pk}),
            {
                'total': 15000,
                'scheduled_date': self.scheduled_date.isoformat(),
                'time_slot_id': self.slot.id,
                'notes': 'Incluye decoracion floral.',
                'expires_at': (timezone.now() + timedelta(hours=2)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        custom_request.refresh_from_db()
        return custom_request

    def test_customer_can_accept_quote_and_create_reserved_order(self):
        custom_request = self.quote_request(self.create_request())
        self.client.force_authenticate(self.customer)

        response = self.client.post(reverse('custom-order-accept', kwargs={'pk': custom_request.pk}))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        custom_request.refresh_from_db()
        order = Order.objects.get()
        self.assertEqual(custom_request.status, CustomOrderRequest.Status.APPROVED)
        self.assertEqual(order.total, 15000)
        self.assertEqual(order.delivery_fee, 1000)
        self.assertEqual(order.items.get().variant, None)
        self.assertIsNotNone(order.payment_expires_at)

    @patch('apps.payments.services.MercadoPagoClient')
    def test_approved_payment_converts_custom_order(self, client_class):
        custom_request = self.quote_request(self.create_request())
        self.client.force_authenticate(self.customer)
        self.client.post(reverse('custom-order-accept', kwargs={'pk': custom_request.pk}))
        order = Order.objects.get()
        Payment.objects.create(
            order=order,
            amount=15000,
            currency='PEN',
            preference_id='preference-123',
            checkout_url='https://checkout.example/preference-123',
        )
        client_class.return_value.get_payment.return_value = {
            'id': 'payment-123',
            'preference_id': 'preference-123',
            'external_reference': str(order.code),
            'transaction_amount': 150.0,
            'currency_id': 'PEN',
            'status': 'approved',
        }

        response = self.client.post(reverse('mercado-pago-webhook'), {'data': {'id': 'payment-123'}}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        custom_request.refresh_from_db()
        self.assertEqual(custom_request.status, CustomOrderRequest.Status.CONVERTED)

    def test_non_admin_cannot_quote_custom_order(self):
        custom_request = self.create_request()

        response = self.client.post(
            reverse('admin-custom-order-quote', kwargs={'pk': custom_request.pk}),
            {},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
