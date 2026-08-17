from django.urls import path
from .views import LandingPageView

app_name = 'landing'

urlpatterns = [
    path('', LandingPageView.as_view(), name='home'),
]
