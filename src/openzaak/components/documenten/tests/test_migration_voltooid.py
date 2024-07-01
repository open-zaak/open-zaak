# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from io import BytesIO

from django.core.files import File
from django.test import override_settings

from openzaak.tests.utils.cmis import CMISMixin, require_cmis
from openzaak.tests.utils.migrations import TestMigrations

from .factories import EnkelvoudigInformatieObjectFactory


@require_cmis
@override_settings(
    CMIS_ENABLED=True,
)
class PopulatevoltooidCMISTest(CMISMixin, TestMigrations):
    migrate_from = "0026_bestandsdeel__voltooid"
    migrate_to = "0027_auto_20230417_1415"
    app = "documenten"

    def setUpBeforeMigration(self, apps):
        BestandsDeel = apps.get_model("documenten", "BestandsDeel")

        eio = EnkelvoudigInformatieObjectFactory.create()
        file = File(BytesIO(b"some data"), name="somefile")
        self.part = BestandsDeel.objects.create(
            informatieobject=None,
            informatieobject_uuid=eio.uuid,
            inhoud=file,
            omvang=file.size,
            volgnummer=1,
        )

        self.requests_before_migration = len(self.adapter.request_history)

        self.assertFalse(self.part._voltooid)

    def test_cmis_not_requested(self):
        """
        test that migration 0027_auto_20230417_1415 doesn't produce additional CMIS calls
        """
        self.assertEqual(
            len(self.adapter.request_history), self.requests_before_migration
        )

        self.part.refresh_from_db()
        self.assertTrue(self.part._voltooid)
