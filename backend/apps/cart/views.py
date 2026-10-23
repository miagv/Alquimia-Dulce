from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, response, status
from rest_framework.views import APIView

from .models import Cart, CartItem
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, UpdateCartItemSerializer
from .services import add_item, get_cart, update_item


def cart_with_items(user):
    cart = get_cart(user)
    return Cart.objects.prefetch_related('items__variant__product').get(pk=cart.pk)


class CartView(APIView):
    def get(self, request):
        return response.Response(CartSerializer(cart_with_items(request.user)).data)

    def delete(self, request):
        CartItem.objects.filter(cart__user=request.user).delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class CartItemCreateView(APIView):
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = add_item(request.user, **serializer.validated_data)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)

        item = CartItem.objects.select_related('variant__product').get(pk=item.pk)
        return response.Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(generics.DestroyAPIView):
    queryset = CartItem.objects.none()

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def patch(self, request, *args, **kwargs):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = update_item(request.user, kwargs['pk'], serializer.validated_data['quantity'])
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)

        item = CartItem.objects.select_related('variant__product').get(pk=item.pk)
        return response.Response(CartItemSerializer(item).data)
