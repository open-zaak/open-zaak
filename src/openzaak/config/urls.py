from django.urls import path

from .views import (
    ExternalConfigView,
)

urlpatterns = [
    path("external/", ExternalConfigView.as_view(), name="config-external"),
]
