# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from pathlib import Path

from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step

from openzaak.components.autorisaties.models import Applicatie
from openzaak.config.setup_configuration.steps.applicatie import (
    ApplicatieConfigurationStep,
)

CONFIG_YAML = Path(__file__).parent / "files/setup_config_applicaties.yaml"


class ApplicatieConfigurationTests(TestCase):
    def test_execute_configuration_step_success(self):
        execute_single_step(ApplicatieConfigurationStep, yaml_source=CONFIG_YAML)

        self.assertEqual(Applicatie.objects.count(), 2)

        applicatie1, applicatie2 = Applicatie.objects.all()

        self.assertEqual(str(applicatie1.uuid), "78591bab-9a00-4887-849c-53b21a67782f")
        self.assertEqual(applicatie1.client_ids, ["user-id", "user-id2"])
        self.assertEqual(applicatie1.label, "applicatie1")
        self.assertTrue(applicatie1.heeft_alle_autorisaties)

        self.assertEqual(str(applicatie2.uuid), "fa0f6d18-5900-4d74-aad4-a748afb2c505")
        self.assertEqual(applicatie2.client_ids, ["user-id2"])
        self.assertEqual(applicatie2.label, "applicatie2")
        self.assertTrue(applicatie2.heeft_alle_autorisaties)

    def test_execute_configuration_step_update_existing(self):
        Applicatie.objects.create(
            uuid="78591bab-9a00-4887-849c-53b21a67782f",
            client_ids=["old-user-id"],
            label="old applicatie1",
        )
        Applicatie.objects.create(
            uuid="fa0f6d18-5900-4d74-aad4-a748afb2c505",
            client_ids=["old-user-id2"],
            label="old applicatie2",
        )

        execute_single_step(ApplicatieConfigurationStep, yaml_source=CONFIG_YAML)

        self.assertEqual(Applicatie.objects.count(), 2)

        applicatie1, applicatie2 = Applicatie.objects.all()

        self.assertEqual(str(applicatie1.uuid), "78591bab-9a00-4887-849c-53b21a67782f")
        self.assertEqual(applicatie1.client_ids, ["user-id", "user-id2"])
        self.assertEqual(applicatie1.label, "applicatie1")
        self.assertTrue(applicatie1.heeft_alle_autorisaties)

        self.assertEqual(str(applicatie2.uuid), "fa0f6d18-5900-4d74-aad4-a748afb2c505")
        self.assertEqual(applicatie2.client_ids, ["user-id2"])
        self.assertEqual(applicatie2.label, "applicatie2")
        self.assertTrue(applicatie2.heeft_alle_autorisaties)

    def test_execute_configuration_step_idempotent(self):
        def assert_applicaties():
            self.assertEqual(Applicatie.objects.count(), 2)

            applicatie1, applicatie2 = Applicatie.objects.all()

            self.assertEqual(
                str(applicatie1.uuid), "78591bab-9a00-4887-849c-53b21a67782f"
            )
            self.assertEqual(applicatie1.client_ids, ["user-id", "user-id2"])
            self.assertEqual(applicatie1.label, "applicatie1")
            self.assertTrue(applicatie1.heeft_alle_autorisaties)

            self.assertEqual(
                str(applicatie2.uuid), "fa0f6d18-5900-4d74-aad4-a748afb2c505"
            )
            self.assertEqual(applicatie2.client_ids, ["user-id2"])
            self.assertEqual(applicatie2.label, "applicatie2")
            self.assertTrue(applicatie2.heeft_alle_autorisaties)

        execute_single_step(ApplicatieConfigurationStep, yaml_source=CONFIG_YAML)
        assert_applicaties()

        execute_single_step(ApplicatieConfigurationStep, yaml_source=CONFIG_YAML)
        assert_applicaties()
