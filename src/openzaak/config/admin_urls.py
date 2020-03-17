from django.urls import path

from .admin_views import NLXInwayView

app_name = "config"

urlpatterns = [
    path(r"nlx-inway", NLXInwayView.as_view(), name="nlx_inway"),
]
