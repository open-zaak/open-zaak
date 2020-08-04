# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Define a dummy ROOT_URLCONF for testing.

This enables us to test (a) view(s), processing the entire request/response
processing stack, including middleware.
"""
from django.urls import path

from rest_framework.response import Response
from rest_framework.views import APIView


class View(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


urlpatterns = [path("test-view", View.as_view())]
