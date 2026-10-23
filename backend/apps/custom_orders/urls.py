from django.urls import path

from .views import (
    AdminCustomOrderListView,
    AdminCustomOrderQuoteView,
    AdminCustomOrderRejectView,
    CustomOrderAcceptView,
    CustomOrderRequestDetailView,
    CustomOrderRequestListCreateView,
)

urlpatterns = [
    path('custom-orders/', CustomOrderRequestListCreateView.as_view(), name='custom-order-list'),
    path('custom-orders/<int:pk>/', CustomOrderRequestDetailView.as_view(), name='custom-order-detail'),
    path('custom-orders/<int:pk>/accept/', CustomOrderAcceptView.as_view(), name='custom-order-accept'),
    path('admin/custom-orders/', AdminCustomOrderListView.as_view(), name='admin-custom-order-list'),
    path('admin/custom-orders/<int:pk>/quote/', AdminCustomOrderQuoteView.as_view(), name='admin-custom-order-quote'),
    path('admin/custom-orders/<int:pk>/reject/', AdminCustomOrderRejectView.as_view(), name='admin-custom-order-reject'),
]
