from django.core.management.base import BaseCommand

from apps.orders.services import expire_pending_orders


class Command(BaseCommand):
    help = 'Cancels expired pending-payment orders and restores their stock.'

    def handle(self, *args, **options):
        expired_count = expire_pending_orders()
        self.stdout.write(self.style.SUCCESS(f'Expired {expired_count} order(s).'))
