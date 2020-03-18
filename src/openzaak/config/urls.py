from django.urls import path

from .views import ConfigDetailView, ConfigWizardView

urlpatterns = [
    path("", ConfigDetailView.as_view(), name="config-detail"),
    path("change", ConfigWizardView.as_view(), name="config-change"),
]
