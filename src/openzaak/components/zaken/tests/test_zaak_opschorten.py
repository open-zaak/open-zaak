from django.test import override_settings, tag

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    ComponentTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.components.zaken.models import (
    Status,
    Zaak,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(
    OPENZAAK_DOMAIN="testserver", LINK_FETCHER="vng_api_common.mocks.link_fetcher_200"
)
class ZaakOpschortenAuthTests(JWTAuthMixin, APITestCase):
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

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)

        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_url = cls.check_for_instance(cls.statustype)

        cls.end_statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)

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

    def _add_catalogi_auth(self, component: ComponentTypes, catalogus, scopes):
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=component,
            scopes=scopes,
            catalogus=catalogus,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            verantwoordelijke_organisatie=517439943,
        )

        self.url = reverse(
            "schortzaakop",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

        self.content = {
            "zaak": {
                "toelichting": "toelichting",
            },
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2023-01-01T00:00:00",
            },
        }

    def test_schort_zaak_op_without_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_schort_zaak_op_with_only_zaken_create_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_schort_zaak_op_with_only_zaken_update_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_schort_zaak_op_with_zaken_scopes(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_schort_zaak_op_with_statussen_toevoegen_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_schort_zaak_op_no_zaaktype_in_auth(self):
        self._add_zaken_auth(
            zaaktype="", scopes=[SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE]
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_schort_zaak_op_with_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc,
            self.zaaktype.catalogus,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_schort_zaak_op_with_end_status(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN])

        content = self.content.copy()

        content["status"]["statustype"] = self.check_for_instance(self.end_statustype)

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "status.nonFieldErrors")
        self.assertEqual(error["code"], "resultaat-does-not-exist")


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakOpschortenValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.zaaktype = ZaakTypeFactory.create(concept=False)
        self.zaaktype_url = reverse(self.zaaktype)

        self.statustype_1 = StatusTypeFactory.create(zaaktype=self.zaaktype)
        self.statustype_url = reverse(self.statustype_1)

        self.statustype_2 = StatusTypeFactory.create(zaaktype=self.zaaktype)

        self.zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            verantwoordelijke_organisatie=517439943,
        )

        self.status = {
            "statustype": f"http://testserver{self.statustype_url}",
            "datumStatusGezet": "2023-01-01T00:00:00",
        }

        self.url = reverse(
            "schortzaakop",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

    def test_schort_zaak_op(self):
        content = {
            "zaak": {"bronorganisatie": 517439943},
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        zaak = Zaak.objects.get()

        self.assertEqual(zaak.zaaktype, self.zaaktype)
        self.assertIsNone(zaak.einddatum)

        _status = Status.objects.get()

        self.assertEqual(_status.zaak, zaak)
        self.assertEqual(_status.statustype, self.statustype_1)
        self.assertEqual(
            _status.datum_status_gezet.isoformat(), "2023-01-01T00:00:00+00:00"
        )

        expected_zaak_url = reverse(zaak)
        expected_status_url = reverse(_status)

        expected_response = {
            "zaak": {
                "archiefactiedatum": None,
                "archiefnominatie": None,
                "archiefstatus": "nog_te_archiveren",
                "betalingsindicatie": "",
                "betalingsindicatieWeergave": "",
                "bronorganisatie": "517439943",
                "communicatiekanaal": "",
                "communicatiekanaalNaam": "",
                "deelzaken": [],
                "eigenschappen": [],
                "einddatum": None,
                "einddatumGepland": None,
                "hoofdzaak": None,
                "identificatie": "ZAAK-2025-0000000001",
                "kenmerken": [],
                "laatsteBetaaldatum": None,
                "omschrijving": "",
                "opdrachtgevendeOrganisatie": "",
                "opschorting": {
                    "eerdereOpschorting": False,
                    "indicatie": False,
                    "reden": "",
                },
                "processobject": {
                    "datumkenmerk": "",
                    "identificatie": "",
                    "objecttype": "",
                    "registratie": "",
                },
                "processobjectaard": "",
                "productenOfDiensten": [],
                "publicatiedatum": None,
                "registratiedatum": "2025-01-01",
                "relevanteAndereZaken": [],
                "resultaat": None,
                "rollen": [],
                "selectielijstklasse": "",
                "startdatum": "2025-01-01",
                "startdatumBewaartermijn": None,
                "status": f"http://testserver{expected_status_url}",
                "toelichting": "",
                "uiterlijkeEinddatumAfdoening": None,
                "url": f"http://testserver{expected_zaak_url}",
                "uuid": str(zaak.uuid),
                "verantwoordelijkeOrganisatie": "517439943",
                "verlenging": None,
                "vertrouwelijkheidaanduiding": "openbaar",
                "zaakgeometrie": None,
                "zaakinformatieobjecten": [],
                "zaakobjecten": [],
                "zaaktype": f"http://testserver{self.zaaktype_url}",
            },
            "status": {
                "datumStatusGezet": "2023-01-01T00:00:00Z",
                "gezetdoor": None,
                "indicatieLaatstGezetteStatus": True,
                "statustoelichting": "",
                "statustype": f"http://testserver{self.statustype_url}",
                "url": f"http://testserver{expected_status_url}",
                "uuid": str(_status.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
                "zaakinformatieobjecten": [],
            },
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_with_empty_status(self):
        content = {
            "zaak": {},
            "status": {},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        statustype = get_validation_errors(response, "status.statustype")
        self.assertEqual(statustype["code"], "required")

        datum = get_validation_errors(response, "status.datumStatusGezet")
        self.assertEqual(datum["code"], "required")

    def test_with_no_status(self):
        content = {
            "zaak": {},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_zaaktype_statustype_relation(self):
        content = {
            "zaak": {},
            "status": self.status
            | {"statustype": self.check_for_instance(StatusTypeFactory.create())},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "status.nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")
