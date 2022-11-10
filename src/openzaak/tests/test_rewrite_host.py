# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path


def test_view(request):
    return HttpResponse(request.get_host())


urlpatterns = [path("", test_view)]


@override_settings(ROOT_URLCONF=__name__, OPENZAAK_REWRITE_HOST=True)
class RewriteHostTests(TestCase):
    def setUp(self):
        super().setUp()
        mocker = patch(
            "openzaak.utils.middleware.get_version_mapping", return_value={"/": "1.0.0"}
        )
        mocker.start()
        self.addCleanup(mocker.stop)

    @override_settings(OPENZAAK_DOMAIN="openzaak.example.com", ALLOWED_HOSTS=["*"])
    def test_overridden_host(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"openzaak.example.com")

    @override_settings(OPENZAAK_DOMAIN="openzaak.example.com:8443", ALLOWED_HOSTS=["*"])
    def test_overridden_host_with_port(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"openzaak.example.com:8443")

    @override_settings(OPENZAAK_DOMAIN="")
    def test_setting_empty(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"testserver")

    @override_settings(OPENZAAK_REWRITE_HOST=False)
    def test_setting_not_empty_but_rewrite_disabled(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"testserver")

    def test_setting_default_unset(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"testserver")

    @override_settings(
        OPENZAAK_DOMAIN="kekw",
        ALLOWED_HOSTS=["kekw", "upstream.proxy"],
        USE_X_FORWARDED_HOST=True,
    )
    def test_with_usage_http_forwarded_host(self):
        """
        System checks check also prevent USE_X_FORWARDED_HOST and OPENZAAK_DOMAIN
        combined usage.
        """
        response = self.client.get("", HTTP_X_FORWARDED_HOST="upstream.proxy")

        self.assertEqual(response.content, b"kekw")
