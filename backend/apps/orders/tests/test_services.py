from datetime import date

from django.test import TestCase

from apps.accounts.models import User
from apps.orders.models import BusinessSettings, Holiday, Order, TimeSlot
from apps.orders.services import is_date_available


class AvailabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer@example.com', 'safe-password')
        self.slot = TimeSlot.objects.get(name='09:00-12:00')
        self.settings = BusinessSettings.objects.get(pk=1)
        self.scheduled_date = date(2027, 1, 15)

    def test_holiday_is_not_available(self):
        Holiday.objects.create(date=self.scheduled_date, name='Holiday')

        self.assertFalse(is_date_available(self.scheduled_date, self.settings.daily_order_capacity))

    def test_daily_capacity_blocks_additional_orders(self):
        for _ in range(self.settings.daily_order_capacity):
            Order.objects.create(
                customer=self.user,
                delivery_method=Order.DeliveryMethod.PICKUP,
                scheduled_date=self.scheduled_date,
                time_slot=self.slot,
            )

        self.assertFalse(is_date_available(self.scheduled_date, self.settings.daily_order_capacity))
