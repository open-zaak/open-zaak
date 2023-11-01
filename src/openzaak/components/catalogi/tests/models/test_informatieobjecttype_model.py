# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from datetime import date

from django.test import TestCase

from ...models import InformatieObjectType
from ..factories import CatalogusFactory, InformatieObjectTypeFactory


class InformatieObjectTypeDatesTests(TestCase):
    """test that beginObject and eindeObject are calculated as expected"""

    def test_begin_einde_object(self):
        catalogus = CatalogusFactory.create()
        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
        )
        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 1),
            datum_einde_geldigheid=date(2020, 2, 12),
        )
        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 12),
        )
        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK2",
            datum_begin_geldigheid=date(2021, 10, 1),
            datum_einde_geldigheid=date(2021, 11, 1),
        )
        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="ZAAK2",
            datum_begin_geldigheid=date(2021, 11, 1),
            datum_einde_geldigheid=date(2021, 12, 11),
        )

        iotypen = InformatieObjectType.objects.with_dates().order_by("pk").all()

        for iotype in iotypen[:3]:
            with self.subTest(iotype.pk):
                self.assertEqual(iotype.begin_object, date(2020, 1, 1))
                self.assertIsNone(iotype.einde_object)

        for iotype in iotypen[3:]:
            with self.subTest(iotype.pk):
                self.assertEqual(iotype.begin_object, date(2021, 10, 1))
                self.assertEqual(iotype.einde_object, date(2021, 12, 11))
