# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from datetime import datetime

from django.test import TestCase

import pytz
from freezegun import freeze_time

from openzaak.import_data.models import Import, ImportStatusChoices
from openzaak.import_data.tasks import remove_imports
from openzaak.import_data.tests.factories import ImportFactory


@freeze_time("2024-01-01 08:00")
class RemoveImportsTests(TestCase):
    def test_simple(self):
        marked_for_removal = (
            ImportFactory(
                status=ImportStatusChoices.pending,
                finished_on=datetime(2023, 12, 25, 6, tzinfo=pytz.utc),
                total=0,
            ),
            ImportFactory(
                status=ImportStatusChoices.finished,
                finished_on=datetime(2023, 12, 24, 23, tzinfo=pytz.utc),
                total=0,
            ),
            ImportFactory(
                status=ImportStatusChoices.error,
                finished_on=datetime(2023, 12, 25, 5, tzinfo=pytz.utc),
                total=0,
            ),
        )

        active_import = ImportFactory(
            status=ImportStatusChoices.active,
            finished_on=datetime(2023, 12, 25, 6, tzinfo=pytz.utc),
            total=0,
        )

        recent_imports = (
            ImportFactory(
                status=ImportStatusChoices.pending,
                finished_on=datetime(2023, 12, 25, 9, tzinfo=pytz.utc),
                total=0,
            ),
            ImportFactory(
                status=ImportStatusChoices.error,
                finished_on=datetime(2023, 12, 25, 10, tzinfo=pytz.utc),
                total=0,
            ),
            ImportFactory(
                status=ImportStatusChoices.finished,
                finished_on=datetime(2023, 12, 25, 11, tzinfo=pytz.utc),
                total=0,
            ),
        )

        remove_imports()

        for import_instance in marked_for_removal:
            with self.subTest(import_instance=import_instance):
                with self.assertRaises(Import.DoesNotExist):
                    Import.objects.get(pk=import_instance.pk)

        for import_instance in (*recent_imports, active_import):
            with self.subTest(import_instance=import_instance):
                self.assertTrue(Import.objects.get(pk=import_instance.pk))
