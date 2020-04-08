from django.urls import path

from .admin_views import (
    ConfigDetailView,
    InternalConfigView,
    NLXConfigView,
    NLXInwayView,
)

app_name = "config"

urlpatterns = [
    path(r"nlx-inway", NLXInwayView.as_view(), name="nlx_inway"),
    path(r"detail", ConfigDetailView.as_view(), name="config-detail"),
    path(r"nlx", NLXConfigView.as_view(), name="config-nlx"),
    path("internal/", InternalConfigView.as_view(), name="config-internal"),
]
