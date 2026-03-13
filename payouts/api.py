import logging

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import views, viewsets
from rest_framework.response import Response

from authentications import APITokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated

from payouts.models import PayoutRequest
from payouts.serializers import PayoutSerializer, PayoutInitSerializer
from payouts.tables import PayoutRequestFilter

from callbacks.models import WhitelistedIP
from pricing.models import BusinessPricingPlan, CountryTax
from utils import get_client_ip
from wallet.models import Wallet

logger = logging.getLogger(__name__)

class PayoutInitView(views.APIView):

    authentication_classes = [APITokenAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        from payouts.tasks import process_payout_request
        try:
            business = request.business
            ip = get_client_ip(request)
            whitelist = cache.get(f"whitelist_{business.id}")
            if whitelist and ip not in whitelist:
                return Response({"error": "Unauthorized IP"}, status=403)

            serializer = PayoutInitSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            amount = serializer.validated_data.get("amount")
            currency = serializer.validated_data.get("currency")
            country = serializer.validated_data.get("country")
            business = request.business
            wallet = Wallet.objects.filter(business=business, currency=currency).first()
            if not wallet:
                return Response({"error": f"No wallet found for currency {currency}"}, status=400)
            
            # Get charges
            charges = BusinessPricingPlan.calculate_charge(business, "MPESA-B2C", amount, currency, country)
            charge = charges if charges else 0

            # Get Taxes
            taxes = CountryTax.compute_tax(country, amount)

            total_deduction = amount + charge + taxes
            if wallet.balance < total_deduction:
                return Response({"error": "Insufficient wallet balance to cover amount, charges, and taxes."}, status=400)
            
            serializer.validated_data["charge"] = charge
            serializer.validated_data["taxes"] = taxes

            payout_request = serializer.save(business=request.business)
            resp_data = PayoutSerializer(payout_request).data
            process_payout_request.apply_async(args=[payout_request.id], countdown=3)
            return Response(resp_data)

        except Exception as e:
            logger.error(f"Error in PayoutInitView: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred. Contact support."}, status=400)


class PayoutRequestViewSet(viewsets.ModelViewSet):

    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PayoutSerializer
    http_method_names = ["get", "head", "options"]
    filterset_class = PayoutRequestFilter

    def get_queryset(self):
        business = self.request.business
        return PayoutRequest.objects.filter(business=business).order_by("-created_at")

    def retrieve(self, request, pk=None):
        pay_request = get_object_or_404(self.get_queryset(), alias_id=pk)
        serializer = PayoutSerializer(pay_request)
        return Response(serializer.data)    
