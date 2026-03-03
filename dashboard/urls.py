from django.urls import path, include

from .views import overview_view

urlpatterns = [
    path("", overview_view, name="dashboard_overview"),
]  