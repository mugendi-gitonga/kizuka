from decimal import Decimal
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator

from django_tables2 import SingleTableMixin
from django_tables2.export.views import ExportMixin
from django_filters.views import FilterView

from payins.models import DepositRequest
from payins.tables import DepositRequestTable, DepositRequestFilter

# Create your views here.


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("payins.view_depositrequest", raise_exception=True),
    name="dispatch",
)
class DepositListView(ExportMixin, SingleTableMixin, FilterView):
    model = DepositRequest
    table_class = DepositRequestTable  # Set this to your DepositRequestTable if you have one
    filterset_class = DepositRequestFilter  # Set this to your DepositRequestFilter if you have one
    export_name = "deposits"
    export_formats = ["xlsx"]
    template_name = "deposit_list.html"
    context_object_name = "deposits"
    paginate_by = 20

    def get_queryset(self):
        business = self.request.business
        return DepositRequest.objects.filter(business=business).order_by("-created_at")
