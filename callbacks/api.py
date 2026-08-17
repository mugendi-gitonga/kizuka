from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentications import APITokenAuthentication
from callbacks.serializers import DepositCallbackSerializer, PayoutCallbackSerializer


PAYIN_EXAMPLE = {
    "id": "DEP_8f3a1c2b9e4d",
    "currency": "KES",
    "amount": "1000.00",
    "charge": "10.00",
    "taxes": "1.60",
    "net_amount": "988.40",
    "phone_number": "254712345678",
    "status": "SUCCESS",
    "message": "Request processed successfully",
    "reference": "ORDER-1234",
    "narration": "Payment for order #1234",
    "provider": "MPESA-C2B",
    "provider_reference": "SFC1234ABC",
    "created_at": "2026-07-23T09:15:00Z",
    "updated_at": "2026-07-23T09:15:42Z",
}

PAYOUT_EXAMPLE = {
    "id": "PYT_2d9c7b1a5f6e",
    "currency": "KES",
    "amount": "5000.00",
    "charge": "25.00",
    "taxes": "4.00",
    "total_amount": "5029.00",
    "phone_number": "254712345678",
    "status": "SUCCESS",
    "message": "Payout completed successfully",
    "reference": "PAYOUT-5678",
    "narration": "Vendor settlement",
    "provider": "MPESA-B2C",
    "provider_reference": "SFD9876XYZ",
    "created_at": "2026-07-23T09:20:00Z",
    "updated_at": "2026-07-23T09:20:55Z",
}


class BaseCallbackStructureView(views.APIView):
    """Documentation-only reference endpoint - returns the exact payload shape POSTed to your callback_url"""

    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(self.example)


@extend_schema(
    tags=["Webhooks"],
    summary="PAYIN callback payload structure",
    description=(
        "This is a reference endpoint, not one you call as part of a normal integration. "
        "It documents the exact JSON body Kizuka POSTs to your configured PAYIN `callback_url` "
        "(set under Dashboard → Integrations → Callbacks) whenever a deposit request changes "
        "status. Note: Kizuka does not currently sign or otherwise authenticate these outbound "
        "requests - there is no secret header to verify the request came from Kizuka."
    ),
    responses=DepositCallbackSerializer,
    examples=[OpenApiExample("PAYIN callback payload", value=PAYIN_EXAMPLE, response_only=True)],
)
class PayinCallbackStructureView(BaseCallbackStructureView):
    example = PAYIN_EXAMPLE


@extend_schema(
    tags=["Webhooks"],
    summary="PAYOUT callback payload structure",
    description=(
        "This is a reference endpoint, not one you call as part of a normal integration. "
        "It documents the exact JSON body Kizuka POSTs to your configured PAYOUT `callback_url` "
        "(set under Dashboard → Integrations → Callbacks) whenever a payout request changes "
        "status. Note: Kizuka does not currently sign or otherwise authenticate these outbound "
        "requests - there is no secret header to verify the request came from Kizuka."
    ),
    responses=PayoutCallbackSerializer,
    examples=[OpenApiExample("PAYOUT callback payload", value=PAYOUT_EXAMPLE, response_only=True)],
)
class PayoutCallbackStructureView(BaseCallbackStructureView):
    example = PAYOUT_EXAMPLE
