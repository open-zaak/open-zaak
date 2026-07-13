# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import tag

from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.constants import InternExtern
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.catalogi.tests.factories import CatalogusFactory
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse


@tag("gh-2165")
class ServiceNormDurationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def setUp(self):
        super().setUp()

        catalogus = CatalogusFactory.create()
        self.catalogus_detail_url = reverse(catalogus)

        self.data = {
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": False,
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [],
            "besluittypen": [],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

    def test_create_zaaktype_without_servicenorm(self):
        zaaktype_list_url = reverse("catalogi:zaaktype-list")

        response = self.client.post(zaaktype_list_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["servicenorm"], None)

        zt = ZaakType.objects.get()
        self.assertEqual(zt.servicenorm_behandeling, None)

        response = self.client.patch(reverse(zt), {"servicenorm": "P1Y"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["servicenorm"], "P1Y")

        zt.refresh_from_db()
        self.assertEqual(zt.servicenorm_behandeling, relativedelta(years=1))

        response = self.client.patch(reverse(zt), {"servicenorm": None})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["servicenorm"], None)

        zt.refresh_from_db()
        self.assertEqual(zt.servicenorm_behandeling, None)

    def test_create_zaaktype_with_servicenorm_P0D(self):
        zaaktype_list_url = reverse("catalogi:zaaktype-list")

        response = self.client.post(
            zaaktype_list_url, self.data | {"servicenorm": "P0D"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
