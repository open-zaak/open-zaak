# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from pathlib import Path

from django.test import TestCase

from django_setup_configuration.exceptions import ConfigurationRunFailed
from django_setup_configuration.test_utils import execute_single_step
from zgw_consumers.test.factories import ServiceFactory

from openzaak.config.setup_configuration.steps import SelectielijstAPIConfigurationStep
from openzaak.selectielijst.models import ReferentieLijstConfig

CONFIG_YAML = Path(__file__).parent / "files/selectielijst_api_config.yml"


class SelectielijstConfigurationTests(TestCase):

    def setUp(self):
        config = ReferentieLijstConfig.get_solo()

        self.initial_service = ServiceFactory(slug="old-selectielijst-api")
        self.initial_default = 2020
        self.initial_allowed = [2017, 2018, 2019, 2020]

        config.service = self.initial_service
        config.default_year = self.initial_default
        config.allowed_years = self.initial_allowed
        config.save()

    def test_configure(self):

        service = ServiceFactory(slug="selectielijst-api")

        execute_single_step(
            SelectielijstAPIConfigurationStep, yaml_source=str(CONFIG_YAML)
        )

        config = ReferentieLijstConfig.get_solo()
        self.assertEqual(config.service, service)

        self.assertEqual(config.default_year, 2025)
        self.assertEqual(config.allowed_years, [2025, 2026, 2027, 2028])

    def test_configure_with_no_service(self):

        with self.assertRaises(ConfigurationRunFailed) as error:
            execute_single_step(
                SelectielijstAPIConfigurationStep, yaml_source=str(CONFIG_YAML)
            )

        self.assertEqual(
            str(error.exception),
            "Service matching query does not exist. (identifier = selectielijst-api)",
        )

        config = ReferentieLijstConfig.get_solo()
        self.assertEqual(config.service, self.initial_service)
        self.assertEqual(config.default_year, self.initial_default)
        self.assertEqual(config.allowed_years, self.initial_allowed)
