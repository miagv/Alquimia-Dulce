from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Address, User
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order, TimeSlot
from apps.orders.services import expire_pending_orders


class CheckoutApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer@example.com', 'SecurePass123!')
        self.address = Address.objects.create(
            user=self.user,
            recipient_name='Customer',
            recipient_phone='999888777',
            district='Lima',
            address_line='Central avenue 123',
        )
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
            stock=5,
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)
        self.slot = TimeSlot.objects.get(name='09:00-12:00')
        self.scheduled_date = timezone.localdate() + timedelta(days=1)
        self.client.force_authenticate(self.user)

    def test_checkout_creates_reserved_order_and_empties_cart(self):
        response = self.client.post(
            reverse('checkout'),
            {
                'delivery_method': Order.DeliveryMethod.DELIVERY,
                'scheduled_date': self.scheduled_date.isoformat(),
                'time_slot_id': self.slot.id,
                'address_id': self.address.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(order.subtotal, 11000)
        self.assertEqual(order.delivery_fee, 1000)
        self.assertEqual(order.total, 12000)
        self.assertIsNotNone(order.payment_expires_at)
        self.assertEqual(CartItem.objects.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)

    def test_expired_reservation_cancels_order_and_restores_stock(self):
        created = self.client.post(
            reverse('checkout'),
            {
                'delivery_method': Order.DeliveryMethod.PICKUP,
                'scheduled_date': self.scheduled_date.isoformat(),
                'time_slot_id': self.slot.id,
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get()
        order.payment_expires_at = timezone.now() - timedelta(seconds=1)
        order.save(update_fields=['payment_expires_at'])

        self.assertEqual(expire_pending_orders(), 1)
        order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertTrue(order.stock_released)
        self.assertEqual(self.variant.stock, 5)

    def test_availability_returns_active_slots_for_a_future_date(self):
        response = self.client.get(reverse('availability'), {'date': self.scheduled_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_available'])
        self.assertEqual(response.data['remaining_capacity'], 20)
        self.assertEqual(len(response.data['time_slots']), 4)
