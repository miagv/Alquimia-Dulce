from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'provider', 'status', 'amount', 'currency', 'external_payment_id', 'updated_at']
    list_filter = ['provider', 'status']
    search_fields = ['order__code', 'external_payment_id', 'preference_id']
    readonly_fields = ['preference_id', 'checkout_url', 'provider_response', 'created_at', 'updated_at']
