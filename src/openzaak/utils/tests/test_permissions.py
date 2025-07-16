# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from openzaak.components.zaken.api.viewsets import ZaakViewSet
from openzaak.utils.permissions import AuthRequired, MultipleObjectsAuthRequired


class AuthRequiredTests(TestCase):
    def setUp(self):
        self.auth = AuthRequired()

    def test_main_resource_missing(self):
        with self.assertRaises(ImproperlyConfigured):
            self.auth.get_main_resource(None)

    @override_settings(DEBUG=True)
    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_bypass(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        drf_request.accepted_renderer = BrowsableAPIRenderer()
        view = ZaakViewSet()
        result = self.auth.has_permission(drf_request, view)

        self.assertTrue(result)


class MultipleObjectsAuthRequiredTests(TestCase):
    def setUp(self):
        self.auth = MultipleObjectsAuthRequired()

    @override_settings(DEBUG=True)
    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_bypass(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        drf_request.accepted_renderer = BrowsableAPIRenderer()
        view = ZaakViewSet()
        result = self.auth.has_permission(drf_request, view)

        self.assertTrue(result)

    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_viewset_classes_missing(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        view = ZaakViewSet()
        view.action = "list"
        view.viewset_classes = None
        result = self.auth.has_permission(drf_request, view)

        self.assertFalse(result)

    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_view_ismixin_and_action_none(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        view = ZaakViewSet()
        view.action = None

        result = self.auth.has_permission(drf_request, view)

        self.assertTrue(result)
