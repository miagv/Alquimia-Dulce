from datetime import time

from django.db import migrations


def create_operating_configuration(apps, schema_editor):
    BusinessSettings = apps.get_model('orders', 'BusinessSettings')
    TimeSlot = apps.get_model('orders', 'TimeSlot')

    BusinessSettings.objects.get_or_create(
        pk=1,
        defaults={
            'delivery_fee': 1000,
            'daily_order_capacity': 20,
            'pickup_location': 'Villa El Salvador',
            'timezone': 'America/Lima',
            'opens_at': time(9, 0),
            'closes_at': time(21, 0),
        },
    )

    slots = [
        ('09:00-12:00', time(9, 0), time(12, 0), 1),
        ('12:00-15:00', time(12, 0), time(15, 0), 2),
        ('15:00-18:00', time(15, 0), time(18, 0), 3),
        ('18:00-21:00', time(18, 0), time(21, 0), 4),
    ]
    for name, starts_at, ends_at, display_order in slots:
        TimeSlot.objects.get_or_create(
            name=name,
            defaults={
                'starts_at': starts_at,
                'ends_at': ends_at,
                'display_order': display_order,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_operating_configuration, migrations.RunPython.noop),
    ]
