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


from .tasks import process_mpesa_c2b_callback


logger = logging.getLogger(__name__)


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


@api_view(http_method_names=["POST", "GET"])
@permission_classes((AllowAny,))
def mpesa_c2b_callback_url(request):
    try:
        payload = request.data
        print(f"Received mpesa deposit callback at: {datetime.now()}: {request.data}")
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
