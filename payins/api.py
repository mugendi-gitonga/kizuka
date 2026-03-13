from django.shortcuts import get_object_or_404
from rest_framework import views, viewsets
from rest_framework.response import Response

from authentications import APITokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated

from payins.models import DepositRequest
from payins.serializers import DepositSerializer, DepositInitSerializer
from payins.tables import DepositRequestFilter


class DepositInitView(views.APIView):

    authentication_classes = [APITokenAuthentication]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        from payins.tasks import send_deposit_request_to_provider   

        serializer = DepositInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deposit_request = serializer.save(business=request.business)
        resp_data = DepositSerializer(deposit_request).data
        send_deposit_request_to_provider.apply_async(args=[deposit_request.id])
        return Response(resp_data)


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
