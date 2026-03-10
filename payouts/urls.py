from django.urls import path, include

from payouts.views import PayoutListView, create_payout_request

urlpatterns = [
    path("payouts/", PayoutListView.as_view(), name="payout_list"),
    path("payouts/create/", create_payout_request, name="create_payout_request"),
]