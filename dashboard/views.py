from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from wallet.models import Wallet, Transaction
from payins.models import DepositRequest

# Create your views here.

@login_required
def overview_view(request):
    """Dashboard overview page"""
    business = request.business
    
    # Get all wallets for the business
    wallets = Wallet.objects.filter(business=business).order_by('currency')
    
    # Get primary wallet (KES) for featured display
    primary_wallet = wallets.filter(currency='KES').first()
    
    # Get recent transactions across all wallets (last 10)
    recent_transactions = Transaction.objects.filter(
        wallet__business=business
    ).select_related('wallet').order_by("-created_at")[:10]
    
    # Get recent deposit requests for reference
    recent_deposits = DepositRequest.objects.filter(
        business=business
    ).order_by("-created_at")[:5]
    
    context = {
        "wallets": wallets,
        "primary_wallet": primary_wallet,
        "recent_transactions": recent_transactions,
        "recent_deposits": recent_deposits,
    }
    
    return render(request, "overview.html", context)