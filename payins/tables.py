import django_filters
import django_tables2   as tables

from django_filters import DateFromToRangeFilter
from django.db.models import Q
from django.contrib.humanize.templatetags.humanize import intcomma

from payins.models import DepositRequest

class DepositRequestFilter(django_filters.FilterSet):
    created_at = DateFromToRangeFilter()

    class Meta:
        model = DepositRequest
        fields = ['created_at', 'status', 'provider']

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(reference__icontains=search_query) |
                Q(narration__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(provider_reference__icontains=search_query) |
                Q(init_response__icontains=search_query) |
                Q(stk_response__icontains=search_query) |
                Q(callback_response__icontains=search_query)
            )
        return queryset


class DepositRequestTable(tables.Table):
    alias = tables.Column(verbose_name="ID", order_by="id")
    amount = tables.Column(verbose_name="Amount")
    paid_amount = tables.Column(verbose_name="Paid Amount")
    # charge = tables.Column(verbose_name="Charge")
    # taxes = tables.Column(verbose_name="Taxes")
    net_amount = tables.Column(verbose_name="Net Amount")

    def render_amount(self, value):
        return f"{intcomma(value)} {self.record.currency}"

    def render_paid_amount(self, value):
        if value is not None:
            return f"{intcomma(value)} {self.record.currency}"
        return "-"

    def render_net_amount(self, value):
        if value is not None:
            return f"{intcomma(value)} {self.record.currency}"
        return "-" 

    def value_created_at(self, value):
        return value.replace(tzinfo=None)

    class Meta:
        model = DepositRequest
        template_name = "django_tables2/bootstrap4.html"
        fields = (
            "alias",
            "phone_number",
            "amount",
            "paid_amount",
            "net_amount",
            "reference",
            "provider",
            "provider_reference",
            "status",
            "created_at",
        )
        attrs = {"class": "table table-striped table-bordered"}
        empty_text = "There are no records yet"
