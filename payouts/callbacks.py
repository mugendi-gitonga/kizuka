import logging

from datetime import datetime

from rest_framework.response import Response
from django.conf import settings

from rest_framework.decorators import (
    permission_classes,
    api_view,
    throttle_classes,
    parser_classes,
    authentication_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

from payouts.tasks import process_mpesa_payout_callback


logger = logging.getLogger(__name__)

# Inbound Safaricom-facing webhook receiver, not a partner-callable endpoint -
# excluded from the generated API docs, same as the payins-side callbacks.
@extend_schema(exclude=True)
@api_view(http_method_names=["POST", "GET"])
@permission_classes((AllowAny,))
def mpesa_payout_callback_url(request):
    try:
        payload = request.data
        print(f"Received MPESA-B2C payout callback at: {datetime.now()}: {request.data}")
        process_mpesa_payout_callback.apply_async(
            (payload,), queue="payout_results", countdown=3
        )
        return Response("Received callback update", 200)
    except Exception as ex:
        logger.error(ex, exc_info=True)
        return Response(
            "Problem experienced while processing your request. If this persists, please contact support.",
            400,
        )
