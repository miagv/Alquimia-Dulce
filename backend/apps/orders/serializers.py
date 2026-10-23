from rest_framework import serializers

from .models import Order, OrderItem, TimeSlot


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['id', 'name', 'starts_at', 'ends_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'variant_size', 'unit_price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    time_slot = TimeSlotSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'code',
            'delivery_method',
            'status',
            'scheduled_date',
            'time_slot',
            'delivery_district',
            'delivery_address_line',
            'delivery_reference',
            'subtotal',
            'delivery_fee',
            'total',
            'notes',
            'payment_expires_at',
            'created_at',
            'updated_at',
            'items',
        ]


class CheckoutSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=Order.DeliveryMethod.choices)
    scheduled_date = serializers.DateField()
    time_slot_id = serializers.IntegerField(min_value=1)
    address_id = serializers.IntegerField(min_value=1, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        if attrs['delivery_method'] == Order.DeliveryMethod.DELIVERY and not attrs.get('address_id'):
            raise serializers.ValidationError({'address_id': 'A delivery address is required.'})
        return attrs
