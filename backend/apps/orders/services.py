from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Address
from apps.cart.models import Cart, CartItem
from apps.catalog.models import ProductVariant

from .models import BusinessSettings, Holiday, Order, OrderItem, TimeSlot


PAYMENT_RESERVATION_MINUTES = 15
ACTIVE_ORDER_STATUSES = [
    Order.Status.PAID,
    Order.Status.PREPARING,
    Order.Status.READY_FOR_PICKUP,
    Order.Status.OUT_FOR_DELIVERY,
]


def local_now(settings):
    return timezone.localtime(timezone.now(), ZoneInfo(settings.timezone))


def active_capacity_orders(scheduled_date):
    return Order.objects.filter(scheduled_date=scheduled_date).filter(
        Q(status__in=ACTIVE_ORDER_STATUSES)
        | Q(
            status=Order.Status.PENDING_PAYMENT,
            payment_expires_at__gt=timezone.now(),
        )
        | Q(status=Order.Status.PENDING_PAYMENT, payment_expires_at__isnull=True)
    )


def is_date_available(scheduled_date, capacity):
    if Holiday.objects.filter(date=scheduled_date, is_active=True).exists():
        return False
    return active_capacity_orders(scheduled_date).count() < capacity


def validate_schedule(scheduled_date, time_slot, settings):
    now = local_now(settings)
    if scheduled_date < now.date():
        raise ValidationError('The selected date has already passed.')
    if scheduled_date == now.date() and time_slot.ends_at <= now.time():
        raise ValidationError('The selected time slot has already ended.')
    if not is_date_available(scheduled_date, settings.daily_order_capacity):
        raise ValidationError('The selected date is not available.')


def checkout(*, user, delivery_method, scheduled_date, time_slot_id, address_id=None, notes=''):
    with transaction.atomic():
        # Locking the singleton serializes capacity checks across simultaneous checkouts.
        settings = BusinessSettings.objects.select_for_update().get(pk=1)
        time_slot = TimeSlot.objects.select_for_update().filter(pk=time_slot_id, is_active=True).first()
        if not time_slot:
            raise ValidationError('The selected time slot is not available.')
        validate_schedule(scheduled_date, time_slot, settings)

        cart = Cart.objects.select_for_update().filter(user=user).first()
        if not cart:
            raise ValidationError('The cart is empty.')
        cart_items = list(CartItem.objects.select_for_update().filter(cart=cart))
        if not cart_items:
            raise ValidationError('The cart is empty.')

        address = None
        delivery_fee = 0
        if delivery_method == Order.DeliveryMethod.DELIVERY:
            address = Address.objects.select_for_update().filter(pk=address_id, user=user).first()
            if not address:
                raise ValidationError('A valid delivery address is required.')
            delivery_fee = settings.delivery_fee

        order_items = []
        subtotal = 0
        for cart_item in cart_items:
            variant = ProductVariant.objects.select_for_update().select_related('product').filter(
                pk=cart_item.variant_id,
                is_active=True,
                product__is_available=True,
            ).first()
            if not variant:
                raise ValidationError('A product in the cart is no longer available.')
            if cart_item.quantity > variant.stock:
                raise ValidationError(f'Insufficient stock for {variant.product.name} ({variant.size}).')

            item_subtotal = variant.price * cart_item.quantity
            subtotal += item_subtotal
            order_items.append(
                OrderItem(
                    variant=variant,
                    product_name=variant.product.name,
                    variant_size=variant.size,
                    unit_price=variant.price,
                    quantity=cart_item.quantity,
                    subtotal=item_subtotal,
                )
            )
            variant.stock -= cart_item.quantity
            variant.save(update_fields=['stock'])

        expires_at = timezone.now() + timedelta(minutes=PAYMENT_RESERVATION_MINUTES)
        order = Order.objects.create(
            customer=user,
            delivery_method=delivery_method,
            scheduled_date=scheduled_date,
            time_slot=time_slot,
            delivery_address=address,
            delivery_district=address.district if address else '',
            delivery_address_line=address.address_line if address else '',
            delivery_reference=address.reference if address else '',
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=subtotal + delivery_fee,
            notes=notes,
            payment_expires_at=expires_at,
        )
        for item in order_items:
            item.order = order
        OrderItem.objects.bulk_create(order_items)
        cart_items_query = CartItem.objects.filter(pk__in=[item.pk for item in cart_items])
        cart_items_query.delete()

        return order


def expire_pending_orders():
    expired_count = 0
    with transaction.atomic():
        orders = Order.objects.select_for_update().filter(
            status=Order.Status.PENDING_PAYMENT,
            payment_expires_at__lte=timezone.now(),
        )
        for order in orders:
            cancel_order_and_restore_stock(order)
            expired_count += 1
    return expired_count


def cancel_order_and_restore_stock(order):
    if not order.stock_released:
        for item in OrderItem.objects.filter(order=order):
            variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
            variant.stock += item.quantity
            variant.save(update_fields=['stock'])
        order.stock_released = True

    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'stock_released', 'updated_at'])
