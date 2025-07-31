from django.test import override_settings, tag

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import (
    Status,
    Zaak,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin


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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

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
