# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from rest_framework.request import Request

from openzaak.utils.middleware import XWarningMiddleware, add_x_warning


class XWarningTests(SimpleTestCase):
    def test_multiple_warnings_are_collected(self):
        request = RequestFactory().get("/")

        add_x_warning(request, "first")
        add_x_warning(request, "second")

        self.assertEqual(getattr(request, "_x_warnings"), ["first", "second"])

    def test_drf_request_stores_on_underlying_request(self):
        django_request = RequestFactory().get("/")
        drf_request = Request(django_request)

        add_x_warning(drf_request, "a warning")

        self.assertEqual(getattr(django_request, "_x_warnings"), ["a warning"])

    def test_middleware_sets_header(self):
        request = RequestFactory().get("/")

        def view(request):
            add_x_warning(request, "first")
            add_x_warning(request, "second")
            return HttpResponse()

        response = XWarningMiddleware(view)(request)

        assert response is not None
        self.assertEqual(response["X-Warning"], "first; second")

    def test_middleware_without_warnings_sets_no_header(self):
        request = RequestFactory().get("/")

        response = XWarningMiddleware(lambda request: HttpResponse())(request)

        assert response is not None
        self.assertNotIn("X-Warning", response)

    def test_middleware_skips_header_for_error_responses(self):
        request = RequestFactory().get("/")

        def view(request):
            add_x_warning(request, "first")
            return HttpResponse(status=400)

        response = XWarningMiddleware(view)(request)

        assert response is not None
        self.assertNotIn("X-Warning", response)

    def test_middleware_without_get_response_returns_none(self):
        request = RequestFactory().get("/")

        response = XWarningMiddleware()(request)

        self.assertIsNone(response)
