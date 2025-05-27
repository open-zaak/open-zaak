# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from django.http import HttpResponseNotFound
from django.test import RequestFactory, TestCase

from vng_api_common.constants import ComponentTypes

from openzaak.config.models import InternalService
from openzaak.utils.middleware import EnabledMiddleware


class EnabledMiddlewareDatabaseQueryTest(TestCase):
    def setUp(self):
        self.middleware = EnabledMiddleware(lambda r: None)
        self.factory = RequestFactory()

    def test_no_db_query_if_no_component_type(self):
        request = self.factory.get("/")

        with self.assertNumQueries(0):
            result = self.middleware.process_view(request, None, None, None)

        self.assertIsNone(result)

    def test_query_and_returns_404_if_disabled(self):
        InternalService.objects.update_or_create(
            api_type=ComponentTypes.zrc, defaults={"enabled": False}
        )

        request = self.factory.get("/zaken/api/v1/")

        with self.assertNumQueries(1):
            response = self.middleware.process_view(request, None, None, None)

        self.assertIsInstance(response, HttpResponseNotFound)

    def test_request_allowed_if_service_enabled(self):
        InternalService.objects.update_or_create(
            api_type=ComponentTypes.zrc, defaults={"enabled": True}
        )

        request = self.factory.get("/zaken/api/v1/")

        with self.assertNumQueries(1):
            response = self.middleware.process_view(request, None, None, None)

        self.assertIsNone(response)
