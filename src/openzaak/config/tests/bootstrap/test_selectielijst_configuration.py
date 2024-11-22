# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed

from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_selectielijst_oas_get

from ...bootstrap.selectielijst import SelectielijstAPIConfigurationStep


@override_settings(
    SELECTIELIJST_API_ROOT="https://selectielijst.example.com/api/v1/",
    SELECTIELIJST_API_OAS="https://selectielijst.example.com/api/v1/schema/openapi.yaml",
)
class SelectielijstConfigurationTests(TestCase):
    def test_configure(self):
        configuration = SelectielijstAPIConfigurationStep()

        configuration.configure()

        config = ReferentieLijstConfig.get_solo()
        self.assertEqual(
            config.service.api_root, "https://selectielijst.example.com/api/v1/"
        )

    @requests_mock.Mocker()
    def test_configuration_check_ok(self, m):
        configuration = SelectielijstAPIConfigurationStep()
        configuration.configure()

        mock_selectielijst_oas_get(m)
        m.get("https://selectielijst.example.com/api/v1/procestypen", json=[])

        configuration.test_configuration()

        self.assertEqual(
            m.last_request.url,
            "https://selectielijst.example.com/api/v1/procestypen",
        )

    @requests_mock.Mocker()
    def test_configuration_check_failures(self, m):
        configuration = SelectielijstAPIConfigurationStep()
        configuration.configure()

        mock_selectielijst_oas_get(m)
        mock_kwargs = (
            {"exc": requests.ConnectTimeout},
            {"exc": requests.ConnectionError},
            {"status_code": 404},
            {"status_code": 403},
            {"status_code": 500},
        )
        for mock_config in mock_kwargs:
            with self.subTest(mock=mock_config):
                m.get(
                    "https://selectielijst.example.com/api/v1/procestypen",
                    **mock_config
                )

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()

    def test_is_configured(self):
        configuration = SelectielijstAPIConfigurationStep()

        configuration.configure()

        self.assertTrue(configuration.is_configured())
