from decimal import Decimal
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from django_tables2 import SingleTableMixin
from django_tables2.export.views import ExportMixin
from django_filters.views import FilterView

from payins.models import DepositRequest
from payins.tables import DepositRequestTable, DepositRequestFilter
from payins.tasks import send_deposit_request_to_provider
from user_accounts.decorators import require_business_role

# Create your views here.


@method_decorator(login_required, name="dispatch")
@method_decorator(
    require_business_role(allowed_roles=["admin", "staff"]), name="dispatch"
)
class DepositListView(ExportMixin, SingleTableMixin, FilterView):
    model = DepositRequest
    table_class = DepositRequestTable  # Set this to your DepositRequestTable if you have one
    filterset_class = DepositRequestFilter  # Set this to your DepositRequestFilter if you have one
    export_name = "deposits"
    export_formats = ["xlsx"]
    template_name = "payins/deposit_list.html"
    context_object_name = "deposits"
    paginate_by = 20

    def get_queryset(self):
        business = self.request.business
        return DepositRequest.objects.filter(business=business).order_by("-created_at")


@login_required
@require_business_role(allowed_roles=["admin", "staff"])
@require_http_methods(["POST"])
def create_deposit_request(request):
    """Create a new deposit request from form submission"""
    try:
        data = json.loads(request.body)
        
        phone_number = data.get('phone_number', '').strip()
        amount = data.get('amount')
        country = data.get('country', 'KE')
        currency = data.get('currency', 'KES')
        provider = data.get('provider', 'MPESA-C2B')
        
        # Validation
        if not phone_number or not amount:
            return JsonResponse({
                'error': 'Phone number and amount are required'
            }, status=400)
        
        try:
            amount = Decimal(amount)
            if amount < 10 and currency == 'KES':
                return JsonResponse({
                    'error': f'Minimum amount is {currency} 10.00'
                }, status=400)
        except:
            return JsonResponse({
                'error': 'Invalid amount'
            }, status=400)
        
        # Create deposit request
        deposit = DepositRequest.objects.create(
            business=request.business,
            phone_number=phone_number,
            amount=amount,
            country=country,
            # currency=currency,
            provider=provider,
        )
        
        # Send to provider asynchronously
        send_deposit_request_to_provider.apply_async(args=[deposit.id])
        
        return JsonResponse({
            'success': True,
            'message': 'Deposit request created. Check your phone for M-Pesa prompt.',
            'deposit_id': deposit.alias_id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)
