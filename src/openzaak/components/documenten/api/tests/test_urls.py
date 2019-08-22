from django.urls import path

from rest_framework.response import Response
from rest_framework.views import APIView


class View(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


urlpatterns = [path("test-view", View.as_view())]
