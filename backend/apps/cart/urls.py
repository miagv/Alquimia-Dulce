from django.urls import path

from .views import CartItemCreateView, CartItemDetailView, CartView

urlpatterns = [
    path('', CartView.as_view(), name='cart-detail'),
    path('items/', CartItemCreateView.as_view(), name='cart-item-create'),
    path('items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),
]
