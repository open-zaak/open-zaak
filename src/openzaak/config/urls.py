from django.urls import path

from .views import InternalConfigView

urlpatterns = [
    path("internal/", InternalConfigView.as_view(), name="config-internal"),
]
