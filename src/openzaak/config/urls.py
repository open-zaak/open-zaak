from django.urls import path

from .views import ConfigDetailView, InternalConfigView, NLXConfigView

urlpatterns = [
    path("", ConfigDetailView.as_view(), name="config-detail"),
    path("nlx/", NLXConfigView.as_view(), name="config-nlx"),
    path("internal/", InternalConfigView.as_view(), name="config-internal"),
]
