from django.urls import path

from .views import (
    ExternalConfigView,
)

urlpatterns = [
    path("exetrnal/", ExternalConfigView.as_view(), name="config-external"),
]
