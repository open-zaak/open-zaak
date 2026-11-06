# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import time_machine
from rest_framework.test import APITestCase

from ..factories import ZaakFactory


class UniqueFriendlyIdentificationTests(APITestCase):
    @time_machine.travel("2019-01-01", tick=False)
    def test_create_zaak_unique_id(self):
        zaak = ZaakFactory.create()
        self.assertEqual(zaak.identificatie, "ZAAK-2019-0000000001")

    def test_create_zaak_unique_id_per_year(self):
        with time_machine.travel("2018-01-01", tick=False):
            zaak1 = ZaakFactory.create()

        with time_machine.travel("2019-01-01", tick=False):
            zaak2 = ZaakFactory.create()

        self.assertEqual(zaak1.identificatie, "ZAAK-2018-0000000001")

        self.assertEqual(zaak2.identificatie, "ZAAK-2019-0000000001")

    @time_machine.travel("2019-01-01", tick=False)
    def test_delete_then_create_zaak_unique_id(self):
        zaak1 = ZaakFactory.create()
        ZaakFactory.create()
        zaak1.delete()
        zaak3 = ZaakFactory.create()

        self.assertEqual(zaak3.identificatie, "ZAAK-2019-0000000003")
