from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product, ProductVariant


class CatalogApiTests(APITestCase):
    def setUp(self):
        self.cakes = Category.objects.create(name='Cakes', slug='cakes')
        self.cookies = Category.objects.create(name='Cookies', slug='cookies')
        self.featured = Product.objects.create(
            category=self.cakes,
            name='Chocolate Cake',
            slug='chocolate-cake',
            description='Chocolate cake',
            is_featured=True,
        )
        ProductVariant.objects.create(
            product=self.featured,
            size='Medium',
            sku='CAKE-MEDIUM',
            price=5500,
            stock=3,
        )
        unavailable = Product.objects.create(
            category=self.cookies,
            name='Vanilla Cookie',
            slug='vanilla-cookie',
            description='Vanilla cookie',
        )
        ProductVariant.objects.create(
            product=unavailable,
            size='Single',
            sku='COOKIE-SINGLE',
            price=500,
            stock=0,
            is_active=False,
        )

    def test_catalog_returns_only_public_available_products(self):
        response = self.client.get(reverse('product-list'), {'category': 'cakes', 'featured': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        product = response.data['results'][0]
        self.assertEqual(product['slug'], 'chocolate-cake')
        self.assertEqual(product['variants'][0]['price'], 5500)

    def test_product_detail_uses_slug(self):
        response = self.client.get(reverse('product-detail', kwargs={'slug': 'chocolate-cake'}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category']['slug'], 'cakes')
