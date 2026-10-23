from django.contrib import admin

from .models import BusinessSettings, Holiday, Order, OrderItem, TimeSlot


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ['pickup_location', 'delivery_fee', 'daily_order_capacity', 'opens_at', 'closes_at']

    def has_add_permission(self, request):
        return not BusinessSettings.objects.exists()


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['name', 'starts_at', 'ends_at', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_active']
    list_filter = ['is_active']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'variant_size', 'unit_price', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['code', 'customer', 'status', 'delivery_method', 'scheduled_date', 'time_slot', 'total']
    list_filter = ['status', 'delivery_method', 'scheduled_date']
    search_fields = ['code', 'customer__email']
    readonly_fields = ['code', 'subtotal', 'delivery_fee', 'total', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
