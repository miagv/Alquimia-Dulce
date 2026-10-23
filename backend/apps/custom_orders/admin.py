from django.contrib import admin

from .models import CustomOrderQuote, CustomOrderRequest


class CustomOrderQuoteInline(admin.StackedInline):
    model = CustomOrderQuote
    extra = 0


@admin.register(CustomOrderRequest)
class CustomOrderRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'scheduled_date', 'time_slot', 'status', 'created_at']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['customer__email', 'theme', 'flavor']
    inlines = [CustomOrderQuoteInline]
