# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from unittest.mock import patch

from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from ...bootstrap.demo import DemoUserStep


@override_settings(
    DEMO_CLIENT_ID="demo-client-id",
    DEMO_SECRET="demo-secret",
)
class DemoConfigurationTests(TestCase):
    def test_configure(self):
        configuration = DemoUserStep()

        configuration.configure()

        app = Applicatie.objects.get()
        self.assertEqual(app.client_ids, ["demo-client-id"])
        self.assertTrue(app.heeft_alle_autorisaties)
        jwt_secret = JWTSecret.objects.get(identifier="demo-client-id")
        self.assertEqual(jwt_secret.secret, "demo-secret")

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.demo.build_absolute_url",
        return_value="http://testserver/zaken",
    )
    def test_configuration_check_ok(self, m, *mocks):
        configuration = DemoUserStep()
        configuration.configure()
        m.get("http://testserver/zaken", json=[])

        configuration.test_configuration()

        self.assertEqual(m.last_request.url, "http://testserver/zaken")
        self.assertEqual(m.last_request.method, "GET")

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.demo.build_absolute_url",
        return_value="http://testserver/zaken",
    )
    def test_configuration_check_failures(self, m, *mocks):
        configuration = DemoUserStep()
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
                m.get("http://testserver/zaken", **mock_config)

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()

    def test_is_configured(self):
        configuration = DemoUserStep()

        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())
