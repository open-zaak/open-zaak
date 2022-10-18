# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.contrib.sites.models import Site
from django.test import TestCase

import requests
import requests_mock

from ...bootstrap.exceptions import SelfTestFailure
from ...bootstrap.site import SiteConfiguration


class SiteConfigurationTests(TestCase):
    def setUp(self):
        super().setUp()

        self.addCleanup(Site.objects.clear_cache)

    def test_set_domain(self):
        configuration = SiteConfiguration(
            domain="localhost:8000", organization_name="ACME"
        )
        configuration.configure()

        site = Site.objects.get_current()
        self.assertEqual(site.domain, "localhost:8000")
        self.assertEqual(site.name, "Open Zaak ACME")

    def test_noop_current_state(self):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.name = "Test server"  # explicit name given
        site.save()

        configuration = SiteConfiguration(domain="testserver", organization_name="ACME")
        configuration.configure()

        site.refresh_from_db()
        self.assertEqual(site.name, "Test server")

    @requests_mock.Mocker()
    def test_configuration_check_ok(self, m):
        m.get("http://localhost:8000/", status_code=200)
        configuration = SiteConfiguration(
            domain="localhost:8000", organization_name="ACME"
        )
        configuration.configure()

        output = configuration.test_configuration()

        self.assertEqual(output[0].id, "domainCheck")

    @requests_mock.Mocker()
    def test_configuration_check_failures(self, m):
        configuration = SiteConfiguration(
            domain="localhost:8000", organization_name="ACME"
        )
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

                with self.assertRaises(SelfTestFailure):
                    configuration.test_configuration()
