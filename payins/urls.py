from django.urls import path, include

from payins.views import DepositListView

urlpatterns = [
    path("deposits/", DepositListView.as_view(), name="deposit_list"),
]