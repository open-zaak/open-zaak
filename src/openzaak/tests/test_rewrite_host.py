# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path

from openzaak.utils import build_absolute_url
from openzaak.utils.checks import check_openzaak_domain


def test_view(request):
    return HttpResponse(request.get_host())


urlpatterns = [path("", test_view), path("zaken/api/v1/zaken", test_view)]


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
    def test_non_api_view_not_overridden(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"testserver")

    @override_settings(OPENZAAK_DOMAIN="openzaak.example.com", ALLOWED_HOSTS=["*"])
    def test_overridden_host(self):
        response = self.client.get("/zaken/api/v1/zaken")

        self.assertEqual(response.content, b"openzaak.example.com")

    @override_settings(OPENZAAK_DOMAIN="openzaak.example.com:8443", ALLOWED_HOSTS=["*"])
    def test_overridden_host_with_port(self):
        response = self.client.get("/zaken/api/v1/zaken")

        self.assertEqual(response.content, b"openzaak.example.com:8443")

    @override_settings(OPENZAAK_DOMAIN="")
    def test_setting_empty(self):
        response = self.client.get("")

        self.assertEqual(response.content, b"testserver")

    @override_settings(
        OPENZAAK_DOMAIN="openzaak.example.com", OPENZAAK_REWRITE_HOST=False
    )
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
        response = self.client.get(
            "/zaken/api/v1/zaken", headers={"x-forwarded-host": "upstream.proxy"}
        )

        self.assertEqual(response.content, b"kekw")

    @override_settings(
        OPENZAAK_DOMAIN="api.example.nl",
        ALLOWED_HOSTS=["api.example.nl", "testserver"],
        FORCE_SCRIPT_NAME="/ozgv-t",
    )
    def test_overridden_host_with_subpath(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1662
        """
        response = self.client.get("/zaken/api/v1/zaken")

        self.assertEqual(response.content, b"api.example.nl")


class BuildAbsoluteUrlTests(SimpleTestCase):
    @override_settings(
        OPENZAAK_DOMAIN="oz.example.com",
        IS_HTTPS=True,
    )
    def test_build_absolute_url_uses_setting(self):
        abs_url = build_absolute_url("/foo")

        self.assertEqual(abs_url, "https://oz.example.com/foo")


@override_settings(
    OPENZAAK_DOMAIN="oz.example.com",
    OPENZAAK_REWRITE_HOST=True,
    ALLOWED_HOSTS=["*"],
    USE_X_FORWARDED_HOST=False,
)
class SystemCheckTests(SimpleTestCase):
    def test_valid_configuration(self):
        errors = check_openzaak_domain(None)

        self.assertEqual(len(errors), 0)

    def test_invalid_pattern_used(self):
        invalid = (
            "http://oz.example.com",
            "https://oz.example.com",
            "oz.example.com/some-path",
            "user:pw@oz.example.com",
            "oz.example.com:badport",
        )
        for bad_pattern in invalid:
            with self.subTest(value=bad_pattern):
                with override_settings(OPENZAAK_DOMAIN=bad_pattern):
                    errors = check_openzaak_domain(None)

                    self.assertEqual(len(errors), 1)
                    self.assertEqual(errors[0].id, "openzaak.settings.E001")

    def test_valid_pattern_used(self):
        valid = (
            "oz.example.com",
            "oz.example.com:8443",
            "localhost:8000",
            "oz.namespace.svc.local",
            "192.168.1.1",
            "192.168.1.1:9000",
        )

        for valid_pattern in valid:
            with self.subTest(value=valid_pattern):
                with override_settings(OPENZAAK_DOMAIN=valid_pattern):
                    errors = check_openzaak_domain(None)

                    self.assertEqual(len(errors), 0)

    @override_settings(USE_X_FORWARDED_HOST=True)
    def test_cannot_be_used_with_use_x_forwarded_host(self):
        errors = check_openzaak_domain(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "openzaak.settings.W001")

    def test_domain_not_in_allowed_hosts(self):
        invalid = (
            ["testserver"],
            ["example.com"],
            ["localhost", "other"],
        )
        for bad_config in invalid:
            with self.subTest(ALLOWED_HOSTS=bad_config):
                with override_settings(ALLOWED_HOSTS=bad_config):
                    errors = check_openzaak_domain(None)

                    self.assertEqual(len(errors), 1)
                    self.assertEqual(errors[0].id, "openzaak.settings.E002")

                with override_settings(OPENZAAK_REWRITE_HOST=False):
                    errors = check_openzaak_domain(None)

                self.assertEqual(len(errors), 0)

    def test_valid_allowed_hosts(self):
        valid = (
            ["oz.example.com", "oz.example.com:443"],
            [".example.com", ".example.com:8443"],
            ["foo", "*"],
        )

        for good_config in valid:
            with self.subTest(ALLOWED_HOSTS=good_config):
                with override_settings(ALLOWED_HOSTS=good_config):
                    errors = check_openzaak_domain(None)

                    self.assertEqual(len(errors), 0)
