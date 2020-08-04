# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from freezegun import freeze_time
from rest_framework.test import APITestCase

from ..factories import ZaakFactory


class UniqueFriendlyIdentificationTests(APITestCase):
    @freeze_time("2019-01-01")
    def test_create_zaak_unique_id(self):
        zaak = ZaakFactory.create()
        self.assertEqual(zaak.identificatie, "ZAAK-2019-0000000001")

    def test_create_zaak_unique_id_per_year(self):
        with freeze_time("2018-01-01"):
            zaak1 = ZaakFactory.create()

        with freeze_time("2019-01-01"):
            zaak2 = ZaakFactory.create()

        self.assertEqual(zaak1.identificatie, "ZAAK-2018-0000000001")

        self.assertEqual(zaak2.identificatie, "ZAAK-2019-0000000001")

    @freeze_time("2019-01-01")
    def test_delete_then_create_zaak_unique_id(self):
        zaak1 = ZaakFactory.create()
        ZaakFactory.create()
        zaak1.delete()
        zaak3 = ZaakFactory.create()

        self.assertEqual(zaak3.identificatie, "ZAAK-2019-0000000003")
