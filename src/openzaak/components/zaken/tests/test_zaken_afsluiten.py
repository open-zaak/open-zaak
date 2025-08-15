# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.factories import RolFactory, ZaakFactory
from openzaak.tests.utils import JWTAuthMixin

User = get_user_model()


def get_full_url(obj):
    return urljoin(f"http://{settings.OPENZAAK_DOMAIN}", reverse(obj))


@tag("convenience-endpoints")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakAfsluitenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalogus = CatalogusFactory.create()
        cls.zaaktype = ZaakTypeFactory.create(concept=False, catalogus=cls.catalogus)
        cls.resultaattype = ResultaatTypeFactory(
            zaaktype=cls.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        cls.statustype = StatusTypeFactory(
            zaaktype=cls.zaaktype,
        )

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        self.url = reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid})

        self.rol = RolFactory.create(
            zaak=self.zaak, roltype__zaaktype=self.zaak.zaaktype
        )

        self.payload = {
            "zaak": {},
            "status": {
                "statustype": get_full_url(self.statustype),
                "datum_status_gezet": "2025-08-10T12:00:00Z",
                "statustoelichting": "Afgesloten via endpoint",
                "gezetdoor": f"http://testserver{reverse(self.rol)}",
            },
            "resultaat": {
                "zaak": get_full_url(self.zaak),
                "resultaattype": get_full_url(self.resultaattype),
                "toelichting": "Behandeld",
            },
        }

    def test_zaak_afsluiten_success(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.zaak.refresh_from_db()
        self.assertEqual(str(self.zaak.einddatum), "2025-08-10")

        status_obj = self.zaak.status_set.get()
        self.assertEqual(status_obj.statustype, self.statustype)
        self.assertEqual(
            status_obj.statustoelichting, self.payload["status"]["statustoelichting"]
        )

        resultaat_obj = self.zaak.resultaat
        self.assertIsNotNone(resultaat_obj)
        self.assertEqual(resultaat_obj.resultaattype, self.resultaattype)
        self.assertEqual(
            resultaat_obj.toelichting, self.payload["resultaat"]["toelichting"]
        )

    def test_zaak_afsluiten_empty_resultaat(self):
        payload = self.payload.copy()
        payload["resultaat"] = {}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zaak_afsluiten_empty_status(self):
        payload = self.payload.copy()
        payload["status"] = {}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zaak_afsluiten_no_zaak(self):
        payload = {
            "status": {
                "statustype": get_full_url(self.statustype),
                "datum_status_gezet": "2025-08-10T12:00:00Z",
                "statustoelichting": "Afgesloten via endpoint",
                "gezetdoor": f"http://testserver{reverse(self.rol)}",
            },
            "resultaat": {
                "zaak": get_full_url(self.zaak),
                "resultaattype": get_full_url(self.resultaattype),
                "toelichting": "Behandeld",
            },
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
