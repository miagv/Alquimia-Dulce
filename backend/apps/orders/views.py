from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, response, status
from rest_framework.views import APIView

from .models import BusinessSettings, Order, TimeSlot
from .serializers import CheckoutSerializer, OrderSerializer, TimeSlotSerializer
from .services import checkout, is_date_available, local_now


class AvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        requested_date = request.query_params.get('date')
        if not requested_date:
            return response.Response({'detail': 'The date query parameter is required.'}, status=400)
        try:
            scheduled_date = date.fromisoformat(requested_date)
        except ValueError:
            return response.Response({'detail': 'Date must use YYYY-MM-DD.'}, status=400)

        settings = BusinessSettings.objects.get(pk=1)
        now = local_now(settings)
        slots = TimeSlot.objects.filter(is_active=True)
        if scheduled_date == now.date():
            slots = slots.filter(ends_at__gt=now.time())
        date_available = (
            scheduled_date >= now.date()
            and slots.exists()
            and is_date_available(scheduled_date, settings.daily_order_capacity)
        )
        remaining_capacity = 0
        if date_available:
            from .services import active_capacity_orders

            remaining_capacity = settings.daily_order_capacity - active_capacity_orders(scheduled_date).count()

        return response.Response(
            {
                'date': scheduled_date,
                'is_available': date_available,
                'remaining_capacity': remaining_capacity,
                'time_slots': TimeSlotSerializer(slots, many=True).data if date_available else [],
            }
        )


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = checkout(user=request.user, **serializer.validated_data)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.select_related('time_slot').prefetch_related('items').get(pk=order.pk)
        return response.Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).select_related('time_slot').prefetch_related('items')


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    lookup_field = 'code'

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).select_related('time_slot').prefetch_related('items')
