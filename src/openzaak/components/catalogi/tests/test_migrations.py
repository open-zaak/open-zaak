# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from openzaak.tests.utils import TestMigrations

from .factories import ZaakTypeFactory


class MigrateDurationFieldTest(TestMigrations):
    migrate_from = "0027_alter_resultaattype_brondatum_archiefprocedure_objecttype"
    migrate_to = "0028_alter_statustype_doorlooptijd"
    app = "catalogi"

    def setUpBeforeMigration(self, apps):
        StatusType = apps.get_model("catalogi", "StatusType")
        ZaakType = apps.get_model("catalogi", "ZaakType")

        zaaktype_pk = ZaakTypeFactory.create().pk
        status_type = StatusType.objects.create(
            zaaktype=ZaakType.objects.get(pk=zaaktype_pk),
            statustypevolgnummer=123,
            doorlooptijd="P5D",
        )

        self.status_type_pk = status_type.pk

    def test_doorlooptijd_values(self):
        # status_type before migration
        StatusType = self.old_apps.get_model("catalogi", "StatusType")
        status_type = StatusType.objects.get(pk=self.status_type_pk)
        self.assertEqual(status_type.doorlooptijd, timedelta(days=5))

        # status_type after migration
        StatusType = self.apps.get_model("catalogi", "StatusType")
        status_type = StatusType.objects.get(pk=self.status_type_pk)
        self.assertEqual(status_type.doorlooptijd, relativedelta(days=+5))

        # accept years and month
        status_type.doorlooptijd = "P1Y5M5D"
        status_type.save()
        self.assertEqual(
            status_type.doorlooptijd, relativedelta(years=+1, months=+5, days=+5)
        )

        # accept null
        status_type.doorlooptijd = None
        status_type.save()
        self.assertIsNone(status_type.doorlooptijd)
