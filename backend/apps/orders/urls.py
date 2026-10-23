from django.urls import path

from .views import AvailabilityView, CheckoutView, OrderDetailView, OrderListView

urlpatterns = [
    path('availability/', AvailabilityView.as_view(), name='availability'),
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<uuid:code>/', OrderDetailView.as_view(), name='order-detail'),
]
