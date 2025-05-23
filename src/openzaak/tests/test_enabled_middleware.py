# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from unittest.mock import patch

from django.http import HttpResponseNotFound
from django.test import RequestFactory, SimpleTestCase

from openzaak.utils.middleware import EnabledMiddleware


class EnabledMiddlewareDatabaseQueryTest(SimpleTestCase):
    def setUp(self):
        self.middleware = EnabledMiddleware(lambda r: None)
        self.factory = RequestFactory()

    @patch("openzaak.utils.middleware.InternalService.objects.filter")
    def test_no_db_query_if_no_component_type(self, mock_filter):
        request = self.factory.get("/")

        with patch.object(self.middleware, "get_component_type", return_value=None):
            result = self.middleware.process_view(request, None, None, None)

        self.assertIsNone(result)
        mock_filter.assert_not_called()

    @patch("openzaak.utils.middleware.InternalService.objects.filter")
    def test_query_and_returns_404_if_disabled(self, mock_filter):
        request = self.factory.get("/zaken/api/v1/")

        with patch.object(self.middleware, "get_component_type", return_value="zaken"):

            response = self.middleware.process_view(request, None, None, None)

        self.assertIsInstance(response, HttpResponseNotFound)
        mock_filter.assert_called_once_with(api_type="zaken", enabled=False)
        mock_filter.return_value.exists.assert_called_once()
