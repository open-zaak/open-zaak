# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings

import requests_mock
from rest_framework.test import APITestCase

from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.components.zaken.tests.utils import get_zaak_response

from ...tests.factories import BesluitFactory


class BesluitPreviousZaakTestCase(APITestCase):
    def test_zaak_local(self):
        besluit = BesluitFactory.create(for_zaak=True)

        zaak_before = besluit.zaak
        zaak_after = ZaakFactory.create()
        besluit.zaak = zaak_after
        besluit.save()

        self.assertEqual(besluit.previous_zaak, zaak_before)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_zaak_external(self):
        zaak_before = "https://external.documenten.nl/api/v1/zaken/19b702ce-1387-42a3-87d9-b070e8c3f43d"
        zaak_after = "https://external.documenten.nl/api/v1/zaken/7ef7d016-b766-4456-a90c-8908eeb19b49"
        zaaktype = "https://external.documenten.nl/api/v1/zaaktype/11b1cfc2-7f7a-4561-aa62-715819ed468c"

        with requests_mock.Mocker() as m:
            m.get(zaak_before, json=get_zaak_response(zaak_before, zaaktype))
            m.get(zaak_after, json=get_zaak_response(zaak_after, zaaktype))

            besluit = BesluitFactory.create(zaak=zaak_before)

            besluit.zaak = zaak_after
            besluit.save()

            self.assertEqual(besluit.previous_zaak, zaak_before)
