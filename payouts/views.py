import json
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from django_tables2 import SingleTableMixin
from django_tables2.export.views import ExportMixin
from django_filters.views import FilterView

from payouts.models import PayoutRequest
from payouts.tables import PayoutRequestTable, PayoutRequestFilter
from payouts.tasks import process_payout_request
from pricing.models import BusinessPricingPlan, CountryTax, PAYOUT_PROVIDER_CHOICES
from user_accounts.decorators import business_admin_required
from wallet.models import Wallet


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("payouts.view_payoutrequest", raise_exception=True),
    name="dispatch",
)
class PayoutListView(ExportMixin, SingleTableMixin, FilterView):
    model = PayoutRequest
    table_class = PayoutRequestTable
    filterset_class = PayoutRequestFilter
    export_name = "payouts"
    export_formats = ["xlsx"]
    template_name = "payouts/payout_list.html"
    context_object_name = "payouts"
    paginate_by = 20

    def get_queryset(self):
        business = self.request.business
        return PayoutRequest.objects.filter(business=business).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        business = self.request.business
        
        # Get available wallets for the business
        wallets = Wallet.objects.filter(business=business)
        context['wallets'] = wallets
        context['payout_providers'] = PAYOUT_PROVIDER_CHOICES
        
        return context


@login_required
@business_admin_required
@require_http_methods(["POST"])
def create_payout_request(request):
    """Create a new payout request from form submission"""
    try:
        data = json.loads(request.body)
        
        phone_number = data.get('phone_number', '').strip()
        amount = data.get('amount')
        country = data.get('country', 'KE')
        currency = data.get('currency', 'KES')
        provider = data.get('provider', 'MPESA-B2C')
        narration = data.get('narration', '').strip()
        
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
        
        # Check wallet balance
        try:
            wallet = Wallet.objects.get(business=request.business, currency=currency)
        except Wallet.DoesNotExist:
            return JsonResponse({
                'error': f'No {currency} wallet found for your business'
            }, status=400)
        
        # Calculate charge and taxes
        charge = BusinessPricingPlan.calculate_charge(
            business=request.business, 
            provider=provider, 
            amount=amount, 
            currency=currency,
            country=country
        )
        
        if charge is None:
            return JsonResponse({
                'error': 'Unable to calculate charges. Please contact support.'
            }, status=400)
        
        taxes = CountryTax.compute_tax(country=country, amount=charge)
        total_amount = amount + charge + taxes
        
        # Check if wallet has sufficient balance
        if wallet.balance < total_amount:
            return JsonResponse({
                'error': f'Insufficient balance. Required: {currency} {total_amount}, Available: {currency} {wallet.balance}'
            }, status=400)
        
        # Create payout request
        payout = PayoutRequest.objects.create(
            business=request.business,
            phone_number=phone_number,
            amount=amount,
            charge=charge,
            taxes=taxes,
            country=country,
            currency=currency,
            provider=provider,
            narration=narration or f"Payout to {phone_number}",
        )
        
        # Process payout asynchronously
        process_payout_request.apply_async(args=[payout.id])
        
        return JsonResponse({
            'success': True,
            'message': 'Payout request created and processing.',
            'payout_id': payout.alias_id,
            'amount': str(amount),
            'charge': str(charge),
            'taxes': str(taxes),
            'total': str(total_amount),
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)
