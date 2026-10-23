from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Address, User


class AccountApiTests(APITestCase):
    def test_customer_can_register_and_obtain_a_token(self):
        registration = self.client.post(
            reverse('register'),
            {
                'email': 'customer@example.com',
                'password': 'SecurePass123!',
                'first_name': 'Ana',
                'last_name': 'Lopez',
                'phone': '999888777',
            },
        )

        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get().email, 'customer@example.com')

        token = self.client.post(
            reverse('token-obtain-pair'),
            {'email': 'customer@example.com', 'password': 'SecurePass123!'},
        )

        self.assertEqual(token.status_code, status.HTTP_200_OK)
        self.assertIn('access', token.data)
        self.assertIn('refresh', token.data)

    def test_customer_only_sees_own_addresses_and_keeps_one_default(self):
        customer = User.objects.create_user('customer@example.com', 'SecurePass123!')
        other_customer = User.objects.create_user('other@example.com', 'SecurePass123!')
        Address.objects.create(
            user=other_customer,
            label='Other',
            recipient_name='Other Customer',
            recipient_phone='999888777',
            district='Lima',
            address_line='Other street 123',
        )
        self.client.force_authenticate(customer)

        first = self.client.post(
            reverse('address-list'),
            {
                'label': 'Home',
                'recipient_name': 'Ana Lopez',
                'recipient_phone': '999888777',
                'district': 'Villa El Salvador',
                'address_line': 'Av. Central 123',
                'is_default': True,
            },
        )
        second = self.client.post(
            reverse('address-list'),
            {
                'label': 'Work',
                'recipient_name': 'Ana Lopez',
                'recipient_phone': '999888777',
                'district': 'Miraflores',
                'address_line': 'Av. Principal 456',
                'is_default': True,
            },
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.filter(user=customer, is_default=True).count(), 1)

        response = self.client.get(reverse('address-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
