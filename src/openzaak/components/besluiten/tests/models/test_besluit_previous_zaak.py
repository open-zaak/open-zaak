# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from rest_framework.test import APITestCase

from openzaak.components.zaken.tests.factories import ZaakFactory

from ...tests.factories import BesluitFactory


class BesluitPreviousZaakTestCase(APITestCase):
    def test_zaak_local(self):
        besluit = BesluitFactory.create(for_zaak=True)

        zaak_before = besluit.zaak
        zaak_after = ZaakFactory.create()
        besluit.zaak = zaak_after
        besluit.save()

        self.assertEqual(besluit.previous_zaak, zaak_before)
