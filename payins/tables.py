import django_filters
import django_tables2 as tables

from django_filters import DateFromToRangeFilter
from django.db.models import Q
from django.contrib.humanize.templatetags.humanize import intcomma

from payins.models import DepositRequest


class DepositRequestFilter(django_filters.FilterSet):
    created_at = DateFromToRangeFilter()
    search = django_filters.CharFilter(method='filter_search', label='Search')

    class Meta:
        model = DepositRequest
        fields = ['created_at', 'status', 'provider', 'search']

    def filter_search(self, queryset, name, value):
        """Handle search across multiple fields"""
        if value:
            queryset = queryset.filter(
                Q(reference__icontains=value) |
                Q(narration__icontains=value) |
                Q(phone_number__icontains=value) |
                Q(alias_id__icontains=value) |
                Q(provider_reference__icontains=value)
            )
        return queryset

    def filter_queryset(self, queryset):
        """Override to handle both request.GET and request.query_params"""
        queryset = super().filter_queryset(queryset)
        
        # Try to get params from either source
        params = getattr(self.request, 'query_params', None)
        if params is None:
            params = self.request.GET
        
        # Handle search parameter
        search_query = params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(reference__icontains=search_query) |
                Q(narration__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(alias_id__icontains=search_query) |
                Q(provider_reference__icontains=search_query)
            )
        
        return queryset


class DepositRequestTable(tables.Table):
    alias_id = tables.Column(verbose_name="ID", order_by="id")
    amount = tables.Column(verbose_name="Amount")
    paid_amount = tables.Column(verbose_name="Paid Amount")
    net_amount = tables.Column(verbose_name="Net Amount")
    status = tables.Column(verbose_name="Status")
    created_at = tables.Column(verbose_name="Date")

    def render_amount(self, value, record):
        return f"{record.currency} {intcomma(value)}"

    def render_paid_amount(self, value, record):
        if value is not None:
            return f"{record.currency} {intcomma(value)}"
        return "-"

    def render_net_amount(self, value, record):
        if value is not None:
            return f"{record.currency} {intcomma(value)}"
        return "-"

    def render_status(self, value):
        """Render status with color coding"""
        status_colors = {
            'PENDING': '<span class="badge badge-warning">Pending</span>',
            'PROCESSING': '<span class="badge badge-info">Processing</span>',
            'SUCCESS': '<span class="badge badge-success">Success</span>',
            'FAILED': '<span class="badge badge-danger">Failed</span>',
        }
        return status_colors.get(value, f'<span class="badge badge-secondary">{value}</span>')

    def render_created_at(self, value):
        """Format datetime without timezone info"""
        if value:
            return value.replace(tzinfo=None).strftime('%b %d, %Y')
        return "-"

    class Meta:
        model = DepositRequest
        template_name = "django_tables2/bootstrap4.html"
        fields = (
            "alias_id",
            "phone_number",
            "provider",
            "amount",
            "paid_amount",
            "net_amount",
            "reference",
            "provider_reference",
            "status",
            "created_at",
        )
        attrs = {"class": "table table-striped table-bordered"}
        empty_text = "There are no deposits yet"
