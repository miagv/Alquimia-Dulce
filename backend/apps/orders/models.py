import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class BusinessSettings(models.Model):
    delivery_fee = models.PositiveIntegerField(default=1000)
    daily_order_capacity = models.PositiveSmallIntegerField(default=20)
    pickup_location = models.CharField(max_length=255, default='Villa El Salvador')
    timezone = models.CharField(max_length=64, default='America/Lima')
    opens_at = models.TimeField(default='09:00')
    closes_at = models.TimeField(default='21:00')

    class Meta:
        verbose_name_plural = 'business settings'
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name='business_settings_singleton'),
        ]

    def __str__(self):
        return 'Business settings'


class TimeSlot(models.Model):
    name = models.CharField(max_length=50, unique=True)
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'starts_at']

    def __str__(self):
        return self.name


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.date}: {self.name}'


class Order(models.Model):
    class DeliveryMethod(models.TextChoices):
        PICKUP = 'pickup', 'Pickup'
        DELIVERY = 'delivery', 'Delivery'

    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pending payment'
        PAID = 'paid', 'Paid'
        PREPARING = 'preparing', 'Preparing'
        READY_FOR_PICKUP = 'ready_for_pickup', 'Ready for pickup'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for delivery'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    delivery_method = models.CharField(max_length=20, choices=DeliveryMethod.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)
    scheduled_date = models.DateField()
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name='orders')
    delivery_address = models.ForeignKey(
        'accounts.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    delivery_district = models.CharField(max_length=100, blank=True)
    delivery_address_line = models.CharField(max_length=255, blank=True)
    delivery_reference = models.CharField(max_length=255, blank=True)
    subtotal = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    payment_expires_at = models.DateTimeField(null=True, blank=True)
    stock_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
        ]

    def __str__(self):
        return f'Order {self.code}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,
        related_name='order_items',
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=180)
    variant_size = models.CharField(max_length=100)
    unit_price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'
