# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.factories import RolFactory, ZaakFactory

User = get_user_model()


def get_full_url(obj):
    return urljoin(f"http://{settings.OPENZAAK_DOMAIN}", reverse(obj))


@tag("convenience-endpoints")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakAfsluitenTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalogus = CatalogusFactory.create()
        cls.zaaktype = ZaakTypeFactory.create(concept=False, catalogus=cls.catalogus)
        cls.resultaattype = ResultaatTypeFactory(zaaktype=cls.zaaktype)
        cls.statustype = StatusTypeFactory(
            zaaktype=cls.zaaktype,
        )

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="test")
        self.client.force_login(self.user)

        self.zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        self.url = reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid})

        rol = RolFactory.create(zaak=self.zaak, roltype__zaaktype=self.zaak.zaaktype)

        self.payload = {
            "zaak": {"einddatum": "2025-08-06"},
            "status": {
                "statustype": get_full_url(self.statustype),
                "datum_status_gezet": "2025-08-01T12:00:00Z",
                "statustoelichting": "Afgesloten via endpoint",
                "gezetdoor": f"http://testserver{reverse(rol)}",
            },
            "resultaat": {
                "zaak": get_full_url(self.zaak),
                "resultaattype": get_full_url(self.resultaattype),
                "toelichting": "Behandeld",
            },
        }

    def test_zaak_afsluiten_success(self):
        response = self.client.post(self.url, self.payload, format="json")
        print(response.status_code)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.zaak.refresh_from_db()
        self.assertEqual(str(self.zaak.einddatum), "2025-08-06")

    def test_zaak_afsluiten_invalid_resultaat(self):
        payload = self.payload.copy()
        payload["resultaat"] = {}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invalid_fields = [
            item["name"] for item in response.data.get("invalid_params", [])
        ]
        self.assertIn("resultaat.zaak", invalid_fields)
        self.assertIn("resultaat.resultaattype", invalid_fields)
