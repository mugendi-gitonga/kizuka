from django.urls import path, include

from payins.views import DepositListView, create_deposit_request

urlpatterns = [
    path("deposits/", DepositListView.as_view(), name="deposit_list"),
    path("deposits/create/", create_deposit_request, name="create_deposit_request"),
]