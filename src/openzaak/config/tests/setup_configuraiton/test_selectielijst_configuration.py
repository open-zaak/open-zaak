# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from pathlib import Path

from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step

from openzaak.config.setup_configuration.steps import SelectielijstAPIConfigurationStep
from openzaak.selectielijst.models import ReferentieLijstConfig

CONFIG_YAML = Path(__file__).parent / "files/selectielijst_api_config.yml"


class SelectielijstConfigurationTests(TestCase):
    def test_configure(self):

        execute_single_step(
            SelectielijstAPIConfigurationStep, yaml_source=str(CONFIG_YAML)
        )

        config = ReferentieLijstConfig.get_solo()
        self.assertEqual(
            config.service.api_root, "https://selectielijst.example.com/api/v1/"
        )
