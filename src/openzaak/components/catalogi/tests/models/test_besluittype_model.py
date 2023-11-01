# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from datetime import date

from django.test import TestCase

from ...models import BesluitType
from ..factories import BesluitTypeFactory, CatalogusFactory


class BesluitTypeDatesTests(TestCase):
    """test that beginObject and eindeObject are calculated as expected"""

    def test_begin_einde_object(self):
        catalogus = CatalogusFactory.create()
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
        )
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 1),
            datum_einde_geldigheid=date(2020, 2, 12),
        )
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 12),
        )
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK2",
            datum_begin_geldigheid=date(2021, 10, 1),
            datum_einde_geldigheid=date(2021, 11, 1),
        )
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK2",
            datum_begin_geldigheid=date(2021, 11, 1),
            datum_einde_geldigheid=date(2021, 12, 11),
        )

        besluittypen = BesluitType.objects.with_dates().order_by("pk").all()

        for besluittype in besluittypen[:3]:
            with self.subTest(besluittype.pk):
                self.assertEqual(besluittype.begin_object, date(2020, 1, 1))
                self.assertIsNone(besluittype.einde_object)

        for besluittype in besluittypen[3:]:
            with self.subTest(besluittype.pk):
                self.assertEqual(besluittype.begin_object, date(2021, 10, 1))
                self.assertEqual(besluittype.einde_object, date(2021, 12, 11))
