# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed

from ...bootstrap.site import SiteConfigurationStep


@override_settings(OPENZAAK_DOMAIN="localhost:8000", OPENZAAK_ORGANIZATION="ACME")
class SiteConfigurationTests(TestCase):
    def setUp(self):
        super().setUp()

        self.addCleanup(Site.objects.clear_cache)

    def test_set_domain(self):
        configuration = SiteConfigurationStep()
        configuration.configure()

        site = Site.objects.get_current()
        self.assertEqual(site.domain, "localhost:8000")
        self.assertEqual(site.name, "Open Zaak ACME")

    @requests_mock.Mocker()
    def test_configuration_check_ok(self, m):
        m.get("http://localhost:8000/", status_code=200)
        configuration = SiteConfigurationStep()
        configuration.configure()

        configuration.test_configuration()

        self.assertEqual(m.last_request.url, "http://localhost:8000/")
        self.assertEqual(m.last_request.method, "GET")

    @requests_mock.Mocker()
    def test_configuration_check_failures(self, m):
        configuration = SiteConfigurationStep()
        configuration.configure()

        mock_kwargs = (
            {"exc": requests.ConnectTimeout},
            {"exc": requests.ConnectionError},
            {"status_code": 404},
            {"status_code": 403},
            {"status_code": 500},
        )
        for mock_config in mock_kwargs:
            with self.subTest(mock=mock_config):
                m.get("http://localhost:8000/", **mock_config)

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()

    def test_is_configured(self):
        configuration = SiteConfigurationStep()

        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())
