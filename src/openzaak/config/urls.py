from django.urls import path

from .views import InternalConfigView, NLXConfigView

urlpatterns = [
    path("nlx/", NLXConfigView.as_view(), name="config-nlx"),
    path("internal/", InternalConfigView.as_view(), name="config-internal"),
]
