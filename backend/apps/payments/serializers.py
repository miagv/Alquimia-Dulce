from rest_framework import serializers

from .models import Payment


class PaymentPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['preference_id', 'checkout_url', 'amount', 'currency', 'status']
