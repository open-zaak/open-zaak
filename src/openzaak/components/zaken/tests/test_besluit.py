# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2025 Dimpact

import uuid

from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.besluiten.constants import VervalRedenen
from openzaak.components.besluiten.models import Besluit
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.utils import (
    get_zaak_response,
    get_zaakbesluit_response,
)
from openzaak.tests.utils import JWTAuthMixin


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitGeforceerdBijwerkenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = False
    base = "https://externe.zaken.nl/api/v1/"

    def _create_closed_zaak(self):
        """Helper to create a closed zaak URL"""
        return f"{self.base}zaken/{uuid.uuid4()}"

    def test_create_besluit_closed_zaak_with_override_scope(self):
        zaak_url = self._create_closed_zaak()
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse('zaaktype-detail', kwargs={'uuid': zaaktype.uuid})}"

        zaakbesluit_data = get_zaakbesluit_response(zaak_url)
        url = reverse("besluit-list", kwargs={"version": "1"})

        # Set JWT scopes
        # self.set_jwt_scopes(["zaken.geforceerd-bijwerken"], component="besluiten")

        with requests_mock.Mocker() as m:
            m.get(zaak_url, json=get_zaak_response(zaak_url, zaaktype_url))
            m.post(f"{zaak_url}/besluiten", json=zaakbesluit_data, status_code=201)

            # Perform POST request
            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",
                    "identificatie": "123123",
                    "besluittype": f"http://testserver{reverse('besluittype-detail', kwargs={'uuid': besluittype.uuid})}",
                    "datum": "2025-09-19",
                    "toelichting": "Test besluit op gesloten zaak",
                    "ingangsdatum": "2025-09-20",
                    "vervaldatum": "2025-12-31",
                    "vervalreden": VervalRedenen.tijdelijk,
                    "zaak": zaak_url,
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        besluit = Besluit.objects.get()
        self.assertEqual(besluit._zaakbesluit_url, zaakbesluit_data["url"])
