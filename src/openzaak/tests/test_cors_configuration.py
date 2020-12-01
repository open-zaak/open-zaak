# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
#
# Documentation on CORS spec, see MDN
# https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request
from unittest.mock import patch

from django.test import override_settings
from django.urls import path

from rest_framework import views
from rest_framework.response import Response
from rest_framework.test import APITestCase

from openzaak.accounts.tests.factories import SuperUserFactory


class View(views.APIView):
    def get(self, request, *args, **kwargs):
        return Response({"ok": True})

    post = get


urlpatterns = [path("cors", View.as_view())]


class CorsMixin:
    def setUp(self):
        super().setUp()
        mocker = patch(
            "openzaak.utils.middleware.get_version_mapping", return_value={"/": "1.0.0"}
        )
        mocker.start()
        self.addCleanup(mocker.stop)


@override_settings(ROOT_URLCONF="openzaak.tests.test_cors_configuration")
class DefaultCORSConfigurationTests(CorsMixin, APITestCase):
    """
    Test the default CORS settings.
    """

    def test_preflight_request(self):
        """
        Test the most basic preflight request.
        """
        response = self.client.options(
            "/cors",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="origin, x-requested-with",
            HTTP_ORIGIN="https://evil.com",
        )

        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_credentialed_request(self):
        user = SuperUserFactory.create(password="secret")
        self.assertTrue(self.client.login(username=user.username, password="secret"))

        response = self.client.get("/cors", HTTP_ORIGIN="https://evil.com",)

        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertNotIn("Access-Control-Allow-Credentials", response)


@override_settings(
    ROOT_URLCONF="openzaak.tests.test_cors_configuration",
    CORS_ALLOW_ALL_ORIGINS=True,
    CORS_ALLOW_CREDENTIALS=False,
)
class CORSEnabledWithoutCredentialsTests(CorsMixin, APITestCase):
    """
    Test the default CORS settings.
    """

    def test_preflight_request(self):
        """
        Test the most basic preflight request.
        """
        response = self.client.options(
            "/cors",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="origin, x-requested-with",
            HTTP_ORIGIN="https://evil.com",
        )

        # wildcard "*" prevents browsers from sending credentials - this is good
        self.assertNotEqual(response["Access-Control-Allow-Origin"], "https://evil.com")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_simple_request(self):
        response = self.client.get("/cors", HTTP_ORIGIN="https://evil.com",)

        # wildcard "*" prevents browsers from sending credentials - this is good
        self.assertNotEqual(response["Access-Control-Allow-Origin"], "https://evil.com")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_credentialed_request(self):
        user = SuperUserFactory.create(password="secret")
        self.assertTrue(self.client.login(username=user.username, password="secret"))

        response = self.client.get("/cors", HTTP_ORIGIN="https://evil.com",)

        # wildcard "*" prevents browsers from sending credentials - this is good
        self.assertNotEqual(response["Access-Control-Allow-Origin"], "https://evil.com")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Credentials", response)


@override_settings(
    ROOT_URLCONF="openzaak.tests.test_cors_configuration",
    CORS_ALLOW_ALL_ORIGINS=True,
    CORS_ALLOW_CREDENTIALS=False,
)
class CORSEnabledWithAuthHeaderTests(CorsMixin, APITestCase):
    def test_preflight_request(self):
        """
        Test a pre-flight request for requests including the HTTP Authorization header.

        The inclusion of htis header makes it a not-simple request, see
        https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#Simple_requests
        """
        response = self.client.options(
            "/cors",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="origin, x-requested-with, authorization",
            HTTP_ORIGIN="https://evil.com",
        )

        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertIn(
            "authorization", response["Access-Control-Allow-Headers"].lower(),
        )
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_credentialed_request(self):
        response = self.client.get(
            "/cors",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_AUTHORIZATION="Bearer foobarbaz",
        )

        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Credentials", response)
