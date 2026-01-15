# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from django.test import override_settings, tag
from django.utils import timezone
from django.utils.translation import gettext as _

from dateutil.relativedelta import relativedelta
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
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.constants import ArchiefNominatieChoices
from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    SCOPEN_ZAKEN_HEROPENEN,
)
from openzaak.components.zaken.models import Resultaat, Status, Zaak
from openzaak.components.zaken.tests.factories import (
    StatusFactory,
    ZaakFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from .utils import ZAAK_READ_KWARGS


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

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)
        cls.resultaattype = ResultaatTypeFactory(
            zaaktype=cls.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            archiefnominatie=ArchiefNominatieChoices.vernietigen,
            archiefactietermijn=relativedelta(years=10),
        )
        cls.resultaattype_url = cls.check_for_instance(cls.resultaattype)

        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_url = cls.check_for_instance(cls.statustype)

        cls.eind_statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)

        cls.eind_statustype_url = cls.check_for_instance(cls.eind_statustype)

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

        self.url = reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid})

        self.content = {
            "zaak": {},
            "status": {
                "statustype": self.eind_statustype_url,
                "datum_status_gezet": "2025-01-01T01:00:00Z",
                "statustoelichting": "Afgesloten via endpoint",
            },
            "resultaat": {
                "resultaattype": self.resultaattype_url,
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

    def test_zaak_afsluiten_with_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc,
            self.zaaktype.catalogus,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_scope_zaken_create_cannot_change_status(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN])

        StatusFactory(zaak=self.zaak)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.assertEqual(
            response.data["detail"],
            _("Met de 'zaken.aanmaken' scope mag je slechts 1 status zetten"),
        )

    def test_reopen_zaak(self):
        self._add_zaken_auth(
            scopes=[SCOPEN_ZAKEN_HEROPENEN, SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        )

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_reopen_zaak_without_force_scope(self):
        self._add_zaken_auth(scopes=[SCOPEN_ZAKEN_HEROPENEN, SCOPE_ZAKEN_BIJWERKEN])

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.assertEqual(
            response.data["detail"],
            _("Je mag geen gegevens aanpassen van een gesloten zaak."),
        )

    def test_reopen_zaak_without_zaken_heropenen_scope(self):
        self._add_zaken_auth(
            scopes=[SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        )

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.assertEqual(
            response.data["detail"],
            _(
                "Het heropenen van een gesloten zaak is niet toegestaan zonder de scope zaken.heropenen"
            ),
        )


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakAfsluitenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.zaaktype = ZaakTypeFactory.create(concept=False)
        self.zaaktype_url = reverse(self.zaaktype)

        self.resultaattype = ResultaatTypeFactory(
            zaaktype=self.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            archiefnominatie=ArchiefNominatieChoices.vernietigen,
            archiefactietermijn=relativedelta(years=10),
        )
        self.resultaattype_url = reverse(self.resultaattype)

        self.statustype_1 = StatusTypeFactory.create(zaaktype=self.zaaktype)
        self.statustype_url_1 = reverse(self.statustype_1)

        self.statustype_2 = StatusTypeFactory.create(zaaktype=self.zaaktype)
        self.statustype_url_2 = reverse(self.statustype_2)

        self.zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            bronorganisatie=517439943,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            verantwoordelijke_organisatie=517439943,
        )

        self.data = {"toelichting": "toelichting"}

        self.status = {
            "statustype": f"http://testserver{self.statustype_url_2}",
            "datumStatusGezet": "2023-01-01T00:00:00",
        }

        self.resultaat = {
            "resultaattype": f"http://testserver{self.resultaattype_url}",
            "toelichting": "Behandeld",
        }

        self.url = reverse(
            "zaakafsluiten",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

    def test_zaak_afsluiten(self):
        content = {
            "zaak": self.data,
            "status": self.status,
            "resultaat": self.resultaat,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        zaak = Zaak.objects.get()

        self.assertEqual(zaak.zaaktype, self.zaaktype)
        self.assertIsNotNone(zaak.einddatum)

        _status = Status.objects.get()

        self.assertEqual(_status.zaak, zaak)
        self.assertEqual(_status.statustype, self.statustype_2)
        self.assertEqual(
            _status.datum_status_gezet.isoformat(), "2023-01-01T00:00:00+00:00"
        )

        resultaat = Resultaat.objects.get()
        self.assertEqual(resultaat.zaak, zaak)
        self.assertEqual(resultaat.resultaattype, self.resultaattype)

        expected_zaak_url = reverse(zaak)
        expected_resultaat_url = reverse(resultaat)
        expected_status_url = reverse(_status)

        expected_response = {
            "zaak": {
                "archiefactiedatum": "2033-01-01",
                "archiefnominatie": ArchiefNominatieChoices.vernietigen,
                "archiefstatus": "nog_te_archiveren",
                "betalingsindicatie": "",
                "betalingsindicatieWeergave": "",
                "bronorganisatie": "517439943",
                "communicatiekanaal": "",
                "communicatiekanaalNaam": "",
                "deelzaken": [],
                "eigenschappen": [],
                "einddatum": "2023-01-01",
                "einddatumGepland": None,
                "laatstGemuteerd": "2025-01-01T12:00:00Z",
                "laatstGeopend": None,
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
                "gerelateerdeZaken": [],
                "resultaat": f"http://testserver{expected_resultaat_url}",
                "rollen": [],
                "selectielijstklasse": "",
                "startdatum": "2025-01-01",
                "startdatumBewaartermijn": "2023-01-01",
                "status": f"http://testserver{expected_status_url}",
                "toelichting": "toelichting",
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
                "statustype": f"http://testserver{self.statustype_url_2}",
                "url": f"http://testserver{expected_status_url}",
                "uuid": str(_status.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
                "zaakinformatieobjecten": [],
            },
            "resultaat": {
                "resultaattype": f"http://testserver{self.resultaattype_url}",
                "toelichting": "Behandeld",
                "url": f"http://testserver{expected_resultaat_url}",
                "uuid": str(resultaat.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
            },
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_zaak_afsluiten_without_resultaat_and_status(self):
        content = {"zaak": self.data}

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        resultaat = get_validation_errors(response, "resultaat")
        self.assertEqual(resultaat["code"], "required")

        _status = get_validation_errors(response, "status")
        self.assertEqual(_status["code"], "required")

    def test_zaak_afsluiten_empty_resultaat(self):
        content = {"zaak": self.data, "resultaat": {}, "status": self.status}

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        resultaattype = get_validation_errors(response, "resultaat.resultaattype")
        self.assertEqual(resultaattype["code"], "required")

    def test_zaak_afsluiten_empty_status(self):
        content = {"zaak": self.data, "status": {}, "resultaat": self.resultaat}

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        statustype = get_validation_errors(response, "status.statustype")
        self.assertEqual(statustype["code"], "required")

        datum = get_validation_errors(response, "status.datumStatusGezet")
        self.assertEqual(datum["code"], "required")

    def test_zaak_afsluiten_empty_zaak(self):
        content = {
            "zaak": self.data,
            "resultaat": self.resultaat,
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_zaak_afsluiten_status_must_be_eindstatus(self):
        content = {
            "zaak": self.data,
            "status": self.status
            | {"statustype": f"http://testserver{self.statustype_url_1}"},
            "resultaat": self.resultaat,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "status.nonFieldErrors")
        self.assertEqual(error["code"], "eindstatus-required")

    def test_zaaktype_statustype_relation(self):
        content = {
            "zaak": {},
            "status": self.status
            | {"statustype": self.check_for_instance(StatusTypeFactory.create())},
            "resultaat": self.resultaat,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "status.nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_zaaktype_resultaattype_relation(self):
        content = {
            "zaak": {},
            "status": self.status,
            "resultaat": self.resultaat
            | {"resultaattype": self.check_for_instance(ResultaatTypeFactory.create())},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "resultaat.nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    @tag("gh-2191")
    def test_zaak_afsluiten_works_with_empty_processobject_gegevensgroep(self):
        """
        Regression test for #2191 to verify that the data returned by GET /zaken
        is valid when used to try and close the zaak
        """
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            bronorganisatie=517439943,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            verantwoordelijke_organisatie=517439943,
            processobject_datumkenmerk="",
            processobject_identificatie="",
            processobject_objecttype="",
            processobject_registratie="",
        )
        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).data
        zaak_data["toelichting"] = "aangepast"
        content = {
            "zaak": zaak_data,
            "status": self.status,
            "resultaat": self.resultaat,
        }

        response = self.client.post(
            reverse(
                "zaakafsluiten",
                kwargs={
                    "uuid": zaak.uuid,
                },
            ),
            content,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
