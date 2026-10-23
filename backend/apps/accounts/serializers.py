from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Address, User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone']
        read_only_fields = ['id', 'email']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id',
            'label',
            'recipient_name',
            'recipient_phone',
            'district',
            'address_line',
            'reference',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        with transaction.atomic():
            address = Address.objects.create(user=user, **validated_data)
            if address.is_default:
                Address.objects.filter(user=user, is_default=True).exclude(pk=address.pk).update(
                    is_default=False
                )
        return address

    def update(self, instance, validated_data):
        with transaction.atomic():
            address = super().update(instance, validated_data)
            if address.is_default:
                Address.objects.filter(user=instance.user, is_default=True).exclude(pk=instance.pk).update(
                    is_default=False
                )
        return address
