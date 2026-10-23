from django.db import models


class Payment(models.Model):
    class Provider(models.TextChoices):
        MERCADO_PAGO = 'mercado_pago', 'Mercado Pago'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='payments')
    provider = models.CharField(max_length=30, choices=Provider.choices, default=Provider.MERCADO_PAGO)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='PEN')
    preference_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    checkout_url = models.URLField(blank=True)
    external_payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider} payment for {self.order}'
