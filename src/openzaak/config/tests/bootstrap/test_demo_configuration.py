# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from pathlib import Path

from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from openzaak.config.setup_configuration.steps import DemoUserStep

DEMO_CONFIG_YAML = Path(__file__).parent / "files/demo_setup_config.yml"


class DemoConfigurationTests(TestCase):
    def test_configure(self):

        execute_single_step(DemoUserStep, yaml_source=str(DEMO_CONFIG_YAML))

        app = Applicatie.objects.get()
        self.assertEqual(app.client_ids, ["demo-client-id"])
        self.assertTrue(app.heeft_alle_autorisaties)
        jwt_secret = JWTSecret.objects.get(identifier="demo-client-id")
        self.assertEqual(jwt_secret.secret, "demo-secret")
