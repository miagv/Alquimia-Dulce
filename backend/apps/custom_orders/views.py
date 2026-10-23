from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, response, status
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer

from .models import CustomOrderRequest
from .permissions import IsStoreAdmin
from .serializers import (
    CreateCustomOrderRequestSerializer,
    CustomOrderRequestSerializer,
    QuoteCustomOrderSerializer,
)
from .services import (
    accept_custom_order_quote,
    create_custom_order_request,
    quote_custom_order,
    reject_custom_order,
)


class CustomOrderRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomOrderRequestSerializer

    def get_queryset(self):
        return CustomOrderRequest.objects.filter(customer=self.request.user).select_related('time_slot').select_related(
            'quote__time_slot', 'quote__order__time_slot'
        )

    def create(self, request, *args, **kwargs):
        serializer = CreateCustomOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            custom_request = create_custom_order_request(user=request.user, **serializer.validated_data)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)
        custom_request = self.get_queryset().get(pk=custom_request.pk)
        return response.Response(CustomOrderRequestSerializer(custom_request).data, status=status.HTTP_201_CREATED)


class CustomOrderRequestDetailView(generics.RetrieveAPIView):
    serializer_class = CustomOrderRequestSerializer

    def get_queryset(self):
        return CustomOrderRequest.objects.filter(customer=self.request.user).select_related('time_slot').select_related(
            'quote__time_slot', 'quote__order__time_slot'
        )


class CustomOrderAcceptView(APIView):
    def post(self, request, pk):
        try:
            order = accept_custom_order_quote(request_id=pk, user=request.user)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)
        order = Order.objects.select_related('time_slot').prefetch_related('items').get(pk=order.pk)
        return response.Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class AdminCustomOrderListView(generics.ListAPIView):
    permission_classes = [IsStoreAdmin]
    serializer_class = CustomOrderRequestSerializer
    queryset = CustomOrderRequest.objects.select_related('time_slot', 'customer').select_related(
        'quote__time_slot', 'quote__order__time_slot'
    )


class AdminCustomOrderQuoteView(APIView):
    permission_classes = [IsStoreAdmin]

    def post(self, request, pk):
        serializer = QuoteCustomOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            quote = quote_custom_order(request_id=pk, **serializer.validated_data)
        except CustomOrderRequest.DoesNotExist:
            return response.Response({'detail': 'Custom order request was not found.'}, status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)
        return response.Response(CustomOrderRequestSerializer(quote.request).data)


class AdminCustomOrderRejectView(APIView):
    permission_classes = [IsStoreAdmin]

    def post(self, request, pk):
        try:
            custom_request = reject_custom_order(request_id=pk)
        except CustomOrderRequest.DoesNotExist:
            return response.Response({'detail': 'Custom order request was not found.'}, status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)
        return response.Response(CustomOrderRequestSerializer(custom_request).data)
