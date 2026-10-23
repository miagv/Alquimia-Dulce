from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import ProductVariant

from .models import Cart, CartItem


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def add_item(user, variant_id, quantity):
    with transaction.atomic():
        cart = get_cart(user)
        variant = ProductVariant.objects.select_for_update().select_related('product').filter(
            pk=variant_id,
            is_active=True,
            product__is_available=True,
        ).first()
        if not variant:
            raise ValidationError('This product variant is not available.')

        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity += quantity

        if item.quantity > variant.stock:
            raise ValidationError('Requested quantity exceeds available stock.')

        item.save()
        return item


def update_item(user, item_id, quantity):
    with transaction.atomic():
        item = CartItem.objects.select_for_update().select_related('variant__product').filter(
            pk=item_id,
            cart__user=user,
        ).first()
        if not item:
            raise ValidationError('Cart item was not found.')
        if not item.variant.is_active or not item.variant.product.is_available:
            raise ValidationError('This product variant is not available.')
        if quantity > item.variant.stock:
            raise ValidationError('Requested quantity exceeds available stock.')

        item.quantity = quantity
        item.save(update_fields=['quantity'])
        return item
