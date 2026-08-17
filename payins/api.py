import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404

from rest_framework.exceptions import ValidationError
from rest_framework import views, viewsets
from rest_framework.response import Response

from authentications import APITokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

from exceptions import UserAdviceException
from payins.models import DepositRequest
from payins.serializers import DepositSerializer, DepositInitSerializer
from payins.tables import DepositRequestFilter
from pricing.models import BusinessAccountLimits

logger = logging.getLogger(__name__)

class DepositInitView(views.APIView):

    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]

    # DepositInitSerializer is only used for manual validation inside post() below,
    # which drf_spectacular can't see - without this, the docs show no request body
    # at all for this endpoint.
    @extend_schema(request=DepositInitSerializer, responses=DepositSerializer)
    def post(self, request, *args, **kwargs):
        from payins.tasks import send_deposit_request_to_provider
        try:
            serializer = DepositInitSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            amount = serializer.validated_data.get("amount")
            currency = serializer.validated_data.get("currency")
            try:
                BusinessAccountLimits.can_collect(request.business, amount, currency)
            except BusinessAccountLimits.DoesNotExist:
                # No limit record configured for this business/currency yet (e.g. not
                # seeded post-launch) - don't hard-block real traffic on missing config.
                logger.warning(f"No BusinessAccountLimits configured for business {request.business.id} / {currency}; skipping limit check")

            deposit_request = serializer.save(business=request.business)
            resp_data = DepositSerializer(deposit_request).data
            send_deposit_request_to_provider.apply_async(args=[deposit_request.id])
            return Response(resp_data)
        except ValidationError as ve:
            logger.error(f"Validation error in DepositInitView: {ve.detail}")
            return Response(ve.detail, status=400)
        except UserAdviceException as e:
            logger.error(f"Account limit error in DepositInitView: {e.detail}")
            return Response({"error": str(e.detail)}, status=e.status_code)
        except Exception as e:
            logger.error(f"Error in DepositInitView: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred. Contact support."}, status=400)


class DepositRequestViewSet(viewsets.ModelViewSet):

    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DepositSerializer
    http_method_names = ["get", "head", "options"]
    filterset_class = DepositRequestFilter

    def get_queryset(self):
        business = self.request.business
        return DepositRequest.objects.filter(business=business).order_by("-created_at")

    def retrieve(self, request, pk=None):
        pay_request = get_object_or_404(self.get_queryset(), alias_id=pk)
        serializer = DepositSerializer(pay_request)
        return Response(serializer.data)
