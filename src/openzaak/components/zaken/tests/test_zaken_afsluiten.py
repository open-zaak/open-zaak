# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings, tag

from dateutil.utils import today
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze,
    ComponentTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from openzaak.components.zaken.tests.factories import (
    RolFactory,
    ZaakFactory,
)
from openzaak.tests.utils import JWTAuthMixin

User = get_user_model()


def get_full_url(obj):
    return urljoin(f"http://{settings.OPENZAAK_DOMAIN}", reverse(obj))


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(
    OPENZAAK_DOMAIN="testserver", LINK_FETCHER="vng_api_common.mocks.link_fetcher_200"
)
class ZaakAfsluitenAuthTests(JWTAuthMixin, APITestCase):
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim

    @classmethod
    def setUpClass(cls):
        APITestCase.setUpClass()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id, defaults={"secret": cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label="for test",
            heeft_alle_autorisaties=False,
        )

        cls.catalogus = CatalogusFactory.create()
        cls.zaaktype = ZaakTypeFactory.create(concept=False, catalogus=cls.catalogus)
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)
        cls.resultaattype = ResultaatTypeFactory(
            zaaktype=cls.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        cls.statustype = StatusTypeFactory(
            zaaktype=cls.zaaktype,
        )

    def _add_zaken_auth(self, zaaktype=None, scopes=None):
        if scopes is None:
            scopes = []

        self.autorisatie = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=scopes,
            zaaktype=self.zaaktype_url if zaaktype is None else zaaktype,
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        self.url = reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid})

        self.rol = RolFactory.create(
            zaak=self.zaak, roltype__zaaktype=self.zaak.zaaktype
        )
        self.resultaattype_url = reverse(self.resultaattype)
        self.statustype_url = self.check_for_instance(self.statustype)

        self.content = {
            "zaak": {},
            "status": {
                "statustype": self.statustype_url,
                "datum_status_gezet": "2025-01-01T01:00:00Z",
                "statustoelichting": "Afgesloten via endpoint",
                "gezetdoor": f"http://testserver{reverse(self.rol)}",
            },
            "resultaat": {
                "zaak": get_full_url(self.zaak),
                "resultaattype": f"http://testserver{self.resultaattype_url}",
                "toelichting": "Behandeld",
            },
        }

    def test_zaak_afsluiten_without_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_zaak_afsluiten_with_only_zaken_create_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_zaak_afsluiten_with_only_zaken_update_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_zaak_afsluiten_with_zaken_scopes(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_zaak_afsluiten_with_statussen_toevoegen_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_zaak_afsluiten_no_zaaktype_in_auth(self):
        self._add_zaken_auth(
            zaaktype="", scopes=[SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE]
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_zaak_afsluiten_already_closed_with_geforceerd_scope(self):
        self._add_zaken_auth(
            scopes=[
                SCOPE_STATUSSEN_TOEVOEGEN,
                SCOPE_ZAKEN_BIJWERKEN,
                SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
            ]
        )
        self.zaak.einddatum = today().date()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)
        response = self.client.post(self.url, self.content, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_zaak_afsluiten_already_closed_without_geforceerd_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_BIJWERKEN])
        self.zaak.einddatum = today().date()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)
        response = self.client.post(self.url, self.content, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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
        self.assertTrue(self.zaak.is_closed)
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

    def test_zaak_afsluiten_status_must_be_eindstatus(self):
        StatusTypeFactory(
            zaaktype=self.zaaktype,
        )
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invalid_params = response.data.get("invalid_params", [])
        error_codes = [err["code"] for err in invalid_params if "code" in err]
        self.assertIn("eindstatus-required", error_codes)
