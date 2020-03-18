from django.urls import path

from .views import ConfigDetailView

urlpatterns = [
    path("", ConfigDetailView.as_view(), name="config-detail"),
]
