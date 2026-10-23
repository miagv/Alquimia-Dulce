from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, response, status
from rest_framework.views import APIView

from .serializers import PaymentPreferenceSerializer
from .services import (
    MercadoPagoApiError,
    MercadoPagoConfigurationError,
    create_payment_preference,
    process_mercado_pago_payment,
    validate_webhook_signature,
)


class PaymentPreferenceView(APIView):
    def post(self, request, code):
        try:
            payment = create_payment_preference(order_code=code, user=request.user)
        except DjangoValidationError as error:
            return response.Response({'detail': error.message}, status=status.HTTP_400_BAD_REQUEST)
        except MercadoPagoConfigurationError as error:
            return response.Response({'detail': str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except MercadoPagoApiError as error:
            return response.Response({'detail': str(error)}, status=status.HTTP_502_BAD_GATEWAY)

        return response.Response(PaymentPreferenceSerializer(payment).data, status=status.HTTP_201_CREATED)


class MercadoPagoWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payment_id = request.query_params.get('data.id') or request.data.get('data', {}).get('id')
        if not payment_id:
            return response.Response({'detail': 'Payment id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not validate_webhook_signature(
            signature=request.headers.get('x-signature'),
            request_id=request.headers.get('x-request-id'),
            payment_id=payment_id,
        ):
            return response.Response({'detail': 'Invalid webhook signature.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            process_mercado_pago_payment(payment_id)
        except (DjangoValidationError, MercadoPagoApiError, MercadoPagoConfigurationError) as error:
            return response.Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return response.Response(status=status.HTTP_204_NO_CONTENT)
