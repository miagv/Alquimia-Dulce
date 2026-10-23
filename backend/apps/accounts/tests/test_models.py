from django.test import TestCase

from apps.accounts.models import User


class UserModelTests(TestCase):
    def test_email_is_used_as_the_login_identifier(self):
        user = User.objects.create_user('CUSTOMER@EXAMPLE.COM', 'safe-password')

        self.assertEqual(user.email, 'CUSTOMER@example.com')
        self.assertTrue(user.check_password('safe-password'))
        self.assertEqual(user.role, User.Role.CUSTOMER)
