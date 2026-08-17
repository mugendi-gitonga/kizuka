import datetime
from collections import Counter

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from wallet.models import Wallet, Transaction
from payins.models import DepositRequest
from payouts.models import PayoutRequest
from pricing.models import TransactionMargin

# Create your views here.

PERIOD_LABELS = {
    "today": "Today",
    "week": "This Week",
    "month": "This Month",
    "year": "This Year",
    "custom": "Custom Range",
}


def _success_rate(success_count, failed_count):
    """Whole-percent rate, matching the whole-percent segments in the status breakdown bar."""
    terminal_count = success_count + failed_count
    if not terminal_count:
        return None
    return round((success_count / terminal_count) * 100)


def _resolve_date_range(request):
    """Returns (period, range_start_date, range_end_date, start_dt, end_dt)."""
    period = request.GET.get("period", "today")
    if period not in PERIOD_LABELS:
        period = "today"

    now = timezone.localtime()
    today = now.date()

    if period == "custom":
        start_date = parse_date(request.GET.get("start", "")) or today
        end_date = parse_date(request.GET.get("end", "")) or today
        if end_date < start_date:
            start_date, end_date = end_date, start_date
    elif period == "week":
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = today
    elif period == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif period == "year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        start_date = today
        end_date = today

    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
    return period, start_date, end_date, start_dt, end_dt


def _build_trend(deposits_qs, payouts_qs, period, start_date, end_date, now):
    """Buckets deposit/payout counts into hourly (today) or daily (otherwise) slots."""
    deposit_timestamps = list(deposits_qs.values_list("created_at", flat=True))
    payout_timestamps = list(payouts_qs.values_list("created_at", flat=True))

    if period == "today":
        keys = list(range(now.hour + 1))
        labels = [f"{h:02d}:00" for h in keys]
        deposit_counts = Counter(timezone.localtime(ts).hour for ts in deposit_timestamps)
        payout_counts = Counter(timezone.localtime(ts).hour for ts in payout_timestamps)
    elif period == "year":
        num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        keys = [
            (start_date.year + (start_date.month - 1 + i) // 12, (start_date.month - 1 + i) % 12 + 1)
            for i in range(num_months)
        ]
        labels = [f"{datetime.date(y, m, 1).strftime('%b')} {y}" for y, m in keys]
        deposit_counts = Counter((lt.year, lt.month) for lt in (timezone.localtime(ts) for ts in deposit_timestamps))
        payout_counts = Counter((lt.year, lt.month) for lt in (timezone.localtime(ts) for ts in payout_timestamps))
    else:
        num_days = (end_date - start_date).days + 1
        keys = [start_date + datetime.timedelta(days=i) for i in range(num_days)]
        labels = [f"{k.strftime('%b')} {k.day}" for k in keys]
        deposit_counts = Counter(timezone.localtime(ts).date() for ts in deposit_timestamps)
        payout_counts = Counter(timezone.localtime(ts).date() for ts in payout_timestamps)

    deposits = [deposit_counts.get(k, 0) for k in keys]
    payouts = [payout_counts.get(k, 0) for k in keys]
    return labels, deposits, payouts


def _cumulative_volume_range_start(now):
    """Timestamp of the earliest successful deposit/payout, or `now` if none exist."""
    earliest_deposit = (
        DepositRequest.objects.filter(status="SUCCESS").order_by("created_at").values_list("created_at", flat=True).first()
    )
    earliest_payout = (
        PayoutRequest.objects.filter(status="SUCCESS").order_by("created_at").values_list("created_at", flat=True).first()
    )
    candidates = [ts for ts in (earliest_deposit, earliest_payout) if ts is not None]
    return min(candidates) if candidates else now


def _build_cumulative_volume_trend(now, range_start_dt=None, num_buckets=30):
    """Cumulative successful deposit+payout volume across at most `num_buckets`
    equal-width buckets, spanning from the earliest successful transaction through
    `now`. Bucket data is computed from real transaction timestamps, but labels are
    generated purely from `now` (one per week, counting back `num_buckets` weeks) so
    the axis always reads as a trailing weekly timeline regardless of how much real
    history actually exists."""
    if range_start_dt is None:
        range_start_dt = _cumulative_volume_range_start(now)
    bucket_width = (now - range_start_dt) / num_buckets

    volumes = [0] * num_buckets
    entries = list(
        DepositRequest.objects.filter(
            status="SUCCESS", created_at__gte=range_start_dt, created_at__lte=now
        ).values_list("created_at", "amount")
    ) + list(
        PayoutRequest.objects.filter(
            status="SUCCESS", created_at__gte=range_start_dt, created_at__lte=now
        ).values_list("created_at", "amount")
    )

    for created_at, amount in entries:
        idx = int((created_at - range_start_dt) / bucket_width)
        idx = max(0, min(idx, num_buckets - 1))
        volumes[idx] += amount or 0

    labels = []
    cumulative = []
    running = 0
    today = now.date()
    for i in range(num_buckets):
        label_date = today - datetime.timedelta(weeks=(num_buckets - 1 - i))
        labels.append(label_date.strftime("%b %d"))
        running += volumes[i]
        cumulative.append(round(float(running), 2))

    return labels, cumulative


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


@staff_member_required
def platform_analytics_view(request):
    """Platform-wide analytics for successful payouts/payins, across every business (staff only)."""
    period, range_start, range_end, start_dt, end_dt = _resolve_date_range(request)

    deposits_qs = DepositRequest.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)
    payouts_qs = PayoutRequest.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)

    deposit_stats = deposits_qs.aggregate(
        total_count=Count("id"),
        success_count=Count("id", filter=Q(status="SUCCESS")),
        failed_count=Count("id", filter=Q(status="FAILED")),
        pending_count=Count("id", filter=Q(status__in=["PENDING", "PROCESSING"])),
        total_volume=Sum("amount", filter=Q(status="SUCCESS")),
    )

    payout_stats = payouts_qs.aggregate(
        total_count=Count("id"),
        success_count=Count("id", filter=Q(status="SUCCESS")),
        failed_count=Count("id", filter=Q(status="FAILED")),
        pending_count=Count("id", filter=Q(status__in=["PENDING", "PROCESSING", "IN_REVIEW"])),
        total_volume=Sum("amount", filter=Q(status="SUCCESS")),
    )

    deposit_by_provider = list(
        deposits_qs.filter(status="SUCCESS")
        .values("provider")
        .annotate(
            count=Count("id"),
            volume=Sum("amount"),
            revenue=Sum("margin__revenue"),
            provider_cost=Sum("margin__provider_cost"),
            net_margin=Sum("margin__margin"),
        )
        .order_by("-volume")
    )
    payout_by_provider = list(
        payouts_qs.filter(status="SUCCESS")
        .values("provider")
        .annotate(
            count=Count("id"),
            volume=Sum("amount"),
            revenue=Sum("margin__revenue"),
            provider_cost=Sum("margin__provider_cost"),
            net_margin=Sum("margin__margin"),
        )
        .order_by("-volume")
    )

    top_businesses_deposits = list(
        deposits_qs.filter(status="SUCCESS")
        .values("business__name")
        .annotate(
            count=Count("id"),
            volume=Sum("amount"),
            revenue=Sum("margin__revenue"),
            provider_cost=Sum("margin__provider_cost"),
            net_margin=Sum("margin__margin"),
        )
        .order_by("-volume")[:10]
    )
    top_businesses_payouts = list(
        payouts_qs.filter(status="SUCCESS")
        .values("business__name")
        .annotate(
            count=Count("id"),
            volume=Sum("amount"),
            revenue=Sum("margin__revenue"),
            provider_cost=Sum("margin__provider_cost"),
            net_margin=Sum("margin__margin"),
        )
        .order_by("-volume")[:10]
    )

    margin_totals = TransactionMargin.objects.filter(
        created_at__gte=start_dt, created_at__lte=end_dt
    ).aggregate(
        total_revenue=Sum("revenue"),
        total_provider_cost=Sum("provider_cost"),
        total_margin=Sum("margin"),
    )

    trend_labels, trend_deposits, trend_payouts = _build_trend(
        deposits_qs, payouts_qs, period, range_start, range_end, timezone.localtime()
    )
    trend_rows = [
        {"label": label, "deposits": deposits, "payouts": payouts}
        for label, deposits, payouts in zip(trend_labels, trend_deposits, trend_payouts)
    ]
    trend_has_data = any(trend_deposits) or any(trend_payouts)

    cumulative_labels, cumulative_volume = _build_cumulative_volume_trend(timezone.localtime())
    cumulative_rows = [
        {"label": label, "volume": volume}
        for label, volume in zip(cumulative_labels, cumulative_volume)
    ]
    cumulative_has_data = any(cumulative_volume)

    context = {
        "deposit_stats": deposit_stats,
        "payout_stats": payout_stats,
        "deposit_success_rate": _success_rate(deposit_stats["success_count"], deposit_stats["failed_count"]),
        "payout_success_rate": _success_rate(payout_stats["success_count"], payout_stats["failed_count"]),
        "overall_success_rate": _success_rate(
            deposit_stats["success_count"] + payout_stats["success_count"],
            deposit_stats["failed_count"] + payout_stats["failed_count"],
        ),
        "deposit_by_provider": deposit_by_provider,
        "payout_by_provider": payout_by_provider,
        "margin_totals": margin_totals,
        "top_businesses_deposits": top_businesses_deposits,
        "top_businesses_payouts": top_businesses_payouts,
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "range_start": range_start,
        "range_end": range_end,
        "trend_labels": trend_labels,
        "trend_deposits": trend_deposits,
        "trend_payouts": trend_payouts,
        "trend_rows": trend_rows,
        "trend_has_data": trend_has_data,
        "cumulative_labels": cumulative_labels,
        "cumulative_volume": cumulative_volume,
        "cumulative_rows": cumulative_rows,
        "cumulative_has_data": cumulative_has_data,
    }
    return render(request, "platform_analytics.html", context)