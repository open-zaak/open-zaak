from django.urls import path

from .views import BatchRequestsView

urlpatterns = [
    path("batch", BatchRequestsView.as_view(), name="batch-requests"),
]
