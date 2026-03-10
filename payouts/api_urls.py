from django.urls import path, include


from payouts.api import PayoutRequestViewSet, PayoutInitView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("payouts", PayoutRequestViewSet, basename="payouts")

urlpatterns = [
    path("payouts/init/", PayoutInitView.as_view(), name="payout_init"),
    path("", include(router.urls)),
]
