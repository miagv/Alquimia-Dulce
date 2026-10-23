from django.urls import path

from .views import MercadoPagoWebhookView, PaymentPreferenceView

urlpatterns = [
    path('orders/<uuid:code>/payment-preference/', PaymentPreferenceView.as_view(), name='payment-preference'),
    path('payments/mercado-pago/webhook/', MercadoPagoWebhookView.as_view(), name='mercado-pago-webhook'),
]
