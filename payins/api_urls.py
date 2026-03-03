from django.urls import path, include


from payins.api import DepositInitView, DepositRequestViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("deposits", DepositRequestViewSet, basename="deposit")

urlpatterns = [
    path("deposits/init/", DepositInitView.as_view(), name="deposit_init"),
    path("", include(router.urls)),
]