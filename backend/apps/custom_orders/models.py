from django.conf import settings
from django.db import models


class CustomOrderRequest(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        QUOTED = 'quoted', 'Quoted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'
        CONVERTED = 'converted', 'Converted'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='custom_order_requests'
    )
    scheduled_date = models.DateField()
    time_slot = models.ForeignKey('orders.TimeSlot', on_delete=models.PROTECT)
    servings = models.PositiveSmallIntegerField()
    flavor = models.CharField(max_length=150)
    theme = models.CharField(max_length=200)
    message = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    reference_image = models.ImageField(upload_to='custom-orders/', blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Custom order #{self.pk}'


class CustomOrderQuote(models.Model):
    request = models.OneToOneField(CustomOrderRequest, on_delete=models.CASCADE, related_name='quote')
    total = models.PositiveIntegerField()
    scheduled_date = models.DateField()
    time_slot = models.ForeignKey('orders.TimeSlot', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    order = models.OneToOneField(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='custom_quote'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Quote for custom order #{self.request_id}'
