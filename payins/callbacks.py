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


from .tasks import process_mpesa_c2b_callback


logger = logging.getLogger(__name__)


# These are inbound Safaricom-facing webhook receivers, not partner-callable
# endpoints - excluded from the generated API docs so they don't show up
# alongside the actual partner API surface.
@extend_schema(exclude=True)
@api_view(http_method_names=["POST", "GET"])
@permission_classes((AllowAny,))
def mpesa_stk_callback_url(request):
    try:
        payload = request.data
        print(f"Received mpesa deposit callback at: {datetime.now()}: {request.data}")
        process_mpesa_c2b_callback.apply_async((True, payload), queue="deposits_results")
        return Response("Received callback update", 200)
    except Exception as ex:
        logger.error(ex, exc_info=True)
        return Response(
            "Problem experienced while processing your request. If this persists, please contact support.",
            400,
        )


@extend_schema(exclude=True)
@api_view(http_method_names=["POST", "GET"])
@permission_classes((AllowAny,))
def mpesa_c2b_callback_url(request):
    try:
        payload = request.data
        print(f"Received mpesa deposit callback at: {datetime.now()}: {request.data}")

        bill_reference = payload.get("BillRefNumber")
        if bill_reference and bill_reference.startswith("STK-"):
            return Response("Received callback update", 200)

        process_mpesa_c2b_callback.apply_async(
            (False, payload), queue="deposits_results", countdown=3
        )
        return Response("Received callback update", 200)
    except Exception as ex:
        logger.error(ex, exc_info=True)
        return Response(
            "Problem experienced while processing your request. If this persists, please contact support.",
            400,
        )
