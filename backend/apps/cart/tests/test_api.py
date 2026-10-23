from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Product, ProductVariant
from apps.cart.models import CartItem


class CartApiTests(APITestCase):
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
        self.client.force_authenticate(self.user)

    def test_cart_is_persistent_and_calculates_prices_server_side(self):
        self.client.get(reverse('cart-detail'))
        self.client.post(reverse('cart-item-create'), {'variant_id': self.variant.id, 'quantity': 1})
        response = self.client.post(reverse('cart-item-create'), {'variant_id': self.variant.id, 'quantity': 2})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.get().quantity, 3)

        cart = self.client.get(reverse('cart-detail'))

        self.assertEqual(cart.data['subtotal'], 16500)
        self.assertEqual(cart.data['items'][0]['unit_price'], 5500)

    def test_cart_rejects_quantities_above_stock(self):
        response = self.client.post(reverse('cart-item-create'), {'variant_id': self.variant.id, 'quantity': 4})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CartItem.objects.count(), 0)
