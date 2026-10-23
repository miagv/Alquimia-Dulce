from rest_framework import serializers

from apps.orders.serializers import OrderSerializer, TimeSlotSerializer

from .models import CustomOrderQuote, CustomOrderRequest


class CustomOrderQuoteSerializer(serializers.ModelSerializer):
    time_slot = TimeSlotSerializer(read_only=True)
    order = OrderSerializer(read_only=True)

    class Meta:
        model = CustomOrderQuote
        fields = [
            'id',
            'total',
            'delivery_fee',
            'scheduled_date',
            'time_slot',
            'notes',
            'expires_at',
            'accepted_at',
            'order',
        ]


class CustomOrderRequestSerializer(serializers.ModelSerializer):
    time_slot = TimeSlotSerializer(read_only=True)
    quote = CustomOrderQuoteSerializer(read_only=True)

    class Meta:
        model = CustomOrderRequest
        fields = [
            'id',
            'delivery_method',
            'delivery_district',
            'delivery_address_line',
            'delivery_reference',
            'delivery_fee',
            'scheduled_date',
            'time_slot',
            'servings',
            'flavor',
            'theme',
            'message',
            'description',
            'reference_image',
            'status',
            'created_at',
            'updated_at',
            'quote',
        ]


class CreateCustomOrderRequestSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=CustomOrderRequest.DeliveryMethod.choices)
    address_id = serializers.IntegerField(min_value=1, required=False)
    scheduled_date = serializers.DateField()
    time_slot_id = serializers.IntegerField(min_value=1)
    servings = serializers.IntegerField(min_value=1, max_value=500)
    flavor = serializers.CharField(max_length=150)
    theme = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField()
    reference_image = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs['delivery_method'] == CustomOrderRequest.DeliveryMethod.DELIVERY and not attrs.get('address_id'):
            raise serializers.ValidationError({'address_id': 'A delivery address is required.'})
        return attrs


class QuoteCustomOrderSerializer(serializers.Serializer):
    total = serializers.IntegerField(min_value=1)
    scheduled_date = serializers.DateField()
    time_slot_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateTimeField()
