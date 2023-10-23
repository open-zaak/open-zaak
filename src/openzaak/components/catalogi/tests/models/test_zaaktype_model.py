# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from datetime import date

from django.test import TestCase

from ...models import ZaakType
from ..factories import CatalogusFactory, ZaakTypeFactory


class ZaakTypeDatesTests(TestCase):
    """test that beginObject and eindeObject are calculated as expected"""

    def test_begin_einde_object(self):
        catalogus = CatalogusFactory.create()
        ZaakTypeFactory.create(
            catalogus=catalogus,
            identificatie="ZAAK1",
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
        )
        ZaakTypeFactory.create(
            catalogus=catalogus,
            identificatie="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 1),
            datum_einde_geldigheid=date(2020, 2, 12),
        )
        ZaakTypeFactory.create(
            catalogus=catalogus,
            identificatie="ZAAK1",
            datum_begin_geldigheid=date(2020, 2, 12),
        )
        ZaakTypeFactory.create(
            catalogus=catalogus,
            identificatie="ZAAK2",
            datum_begin_geldigheid=date(2021, 10, 1),
            datum_einde_geldigheid=date(2021, 11, 1),
        )
        ZaakTypeFactory.create(
            catalogus=catalogus,
            identificatie="ZAAK2",
            datum_begin_geldigheid=date(2021, 11, 1),
            datum_einde_geldigheid=date(2021, 12, 11),
        )

        zaaktypen = (
            ZaakType.objects.with_dates(id_field="identificatie").order_by("pk").all()
        )

        for zaaktype in zaaktypen[:3]:
            with self.subTest(zaaktype.pk):
                self.assertEqual(zaaktype.begin_object, date(2020, 1, 1))
                self.assertIsNone(zaaktype.einde_object)

        for zaaktype in zaaktypen[3:]:
            with self.subTest(zaaktype.pk):
                self.assertEqual(zaaktype.begin_object, date(2021, 10, 1))
                self.assertEqual(zaaktype.einde_object, date(2021, 12, 11))
