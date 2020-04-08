from django.urls import path

from .admin_views import ConfigDetailView, NLXInwayView

app_name = "config"

urlpatterns = [
    path(r"nlx-inway", NLXInwayView.as_view(), name="nlx_inway"),
    path(r"detail", ConfigDetailView.as_view(), name="config-detail"),
]
