# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from zgw_consumers.constants import APITypes

from openzaak.tests.utils import TestMigrations


class MigrateSelectielijstApiRootToService(TestMigrations):
    migrate_from = "0007_alter_referentielijstconfig_default_year"
    migrate_to = "0008_remove_referentielijstconfig_api_root_and_more"
    app = "selectielijst"

    def setUpBeforeMigration(self, apps):
        Service = apps.get_model("zgw_consumers", "Service")
        ReferentielijstConfig = apps.get_model("selectielijst", "ReferentielijstConfig")

        self.api_root = "https://external.selectielijst.nl/api/v1/"
        self.config = ReferentielijstConfig.objects.get()
        self.config.api_root = self.api_root
        self.config.save()

        self.other_selectielijst = Service.objects.create(
            label="other selectielijst",
            slug="other-selectielijst",
            api_type=APITypes.orc,
            api_root="https://other-selectielijst.nl/api/v1/",
        )
        self.selectielijst = Service.objects.create(
            label="selectielijst",
            slug="selectielijst",
            api_type=APITypes.orc,
            api_root=self.api_root,
        )

    def test_correct_service_is_linked_to_config(self):
        """
        Verify that the Service linked to the config if it already existed
        """
        ReferentielijstConfig = self.apps.get_model(
            "selectielijst", "ReferentielijstConfig"
        )

        config = ReferentielijstConfig.objects.get()

        self.assertEqual(config.service.pk, self.selectielijst.pk)
        self.assertEqual(config.service.api_root, self.api_root)


class MigrateSelectielijstApiRootToServiceMissingService(TestMigrations):
    migrate_from = "0007_alter_referentielijstconfig_default_year"
    migrate_to = "0008_remove_referentielijstconfig_api_root_and_more"
    app = "selectielijst"

    def setUpBeforeMigration(self, apps):
        Service = apps.get_model("zgw_consumers", "Service")
        ReferentielijstConfig = apps.get_model("selectielijst", "ReferentielijstConfig")

        self.api_root = "https://external.selectielijst.nl/api/v1/"
        self.config = ReferentielijstConfig.objects.get()
        self.config.api_root = self.api_root
        self.config.save()

        self.other_selectielijst = Service.objects.create(
            label="other selectielijst",
            slug="other-selectielijst",
            api_type=APITypes.orc,
            api_root="https://other-selectielijst.nl/api/v1/",
        )

    def test_correct_service_is_linked_to_config(self):
        """
        Verify that the Service is created if did not exist yet
        """
        ReferentielijstConfig = self.apps.get_model(
            "selectielijst", "ReferentielijstConfig"
        )

        config = ReferentielijstConfig.objects.get()

        self.assertEqual(config.service.api_root, self.api_root)
        self.assertEqual(config.service.label, "VNG Selectielijst")
        self.assertEqual(config.service.slug, "vng-selectielijst")
        self.assertEqual(config.service.api_type, APITypes.orc)
        self.assertEqual(config.service.oas, self.api_root)
