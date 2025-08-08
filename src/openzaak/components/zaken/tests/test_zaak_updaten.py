# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
import datetime

from django.test import override_settings, tag
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze,
    ComponentTypes,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import (
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from openzaak.components.zaken.models import Rol, Status, Zaak, ZaakKenmerk
from openzaak.components.zaken.tests.factories import (
    ResultaatFactory,
    RolFactory,
    ZaakFactory,
    ZaakKenmerkFactory,
)
from openzaak.components.zaken.tests.test_rol import BETROKKENE
from openzaak.tests.utils import JWTAuthMixin


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(
    OPENZAAK_DOMAIN="testserver", LINK_FETCHER="vng_api_common.mocks.link_fetcher_200"
)
class ZaakUpdatenAuthTests(JWTAuthMixin, APITestCase):
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

        cls.roltype = RolTypeFactory(zaaktype=cls.zaaktype)
        cls.roltype_url = cls.check_for_instance(cls.roltype)

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
            "updatezaak",
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
            "rollen": [
                {
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": self.roltype_url,
                    "roltoelichting": "abc",
                }
            ],
        }

    def test_update_zaak_without_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_update_zaak_with_only_zaken_update_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_update_zaak_with_valid_scopes(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_zaak_with_statussen_toevoegen_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_BIJWERKEN])
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_zaak_with_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc,
            self.zaaktype.catalogus,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_zaak_with_end_status(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN])

        content = self.content.copy()

        content["status"]["statustype"] = self.check_for_instance(self.end_statustype)

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "status.nonFieldErrors")
        self.assertEqual(error["code"], "resultaat-does-not-exist")

    def test_update_zaak_with_closed_zaak(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN])

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(
            response.data["detail"],
            "Je mag geen gegevens aanpassen van een gesloten zaak.",
        )

    def test_update_zaak_with_closed_zaak_with_force_scope(self):
        self._add_zaken_auth(
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        )

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_zaak_with_closed_zaak_without_rollen(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN])

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        content = self.content
        content.pop("rollen")

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)


@tag("convenience-endpoints")
@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakUpdatenValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.zaaktype = ZaakTypeFactory.create(concept=False)
        self.zaaktype_url = reverse(self.zaaktype)

        self.roltype = RolTypeFactory(zaaktype=self.zaaktype)
        self.roltype_url = reverse(self.roltype)

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

        self.status = {
            "statustype": f"http://testserver{self.statustype_url_1}",
            "datumStatusGezet": "2023-01-01T00:00:00",
        }

        self.opschorting = {
            "opschorting": {"indicatie": True, "reden": "test"},
        }

        self.rol = {
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "abc",
        }

        self.url = reverse(
            "updatezaak",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

    def test_update_zaak(self):
        content = {
            "zaak": self.opschorting,
            "status": self.status,
            "rollen": [self.rol],
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

        rol = Rol.objects.get()

        self.assertEqual(rol.zaak, zaak)
        self.assertEqual(rol.betrokkene, BETROKKENE)
        self.assertEqual(rol.roltype, self.roltype)

        expected_zaak_url = reverse(zaak)
        expected_rol_url = reverse(rol)
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
                    "eerdereOpschorting": True,
                    "indicatie": True,
                    "reden": "test",
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
                "rollen": [
                    f"http://testserver{expected_rol_url}",
                ],
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
                "statustype": f"http://testserver{self.statustype_url_1}",
                "url": f"http://testserver{expected_status_url}",
                "uuid": str(_status.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
                "zaakinformatieobjecten": [],
            },
            "rollen": [
                {
                    "afwijkendeNaamBetrokkene": "",
                    "authenticatieContext": None,
                    "beginGeldigheid": None,
                    "betrokkene": "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                    "betrokkeneIdentificatie": None,
                    "betrokkeneType": "natuurlijk_persoon",
                    "contactpersoonRol": {
                        "emailadres": "",
                        "functie": "",
                        "naam": "",
                        "telefoonnummer": "",
                    },
                    "eindeGeldigheid": None,
                    "indicatieMachtiging": "",
                    "omschrijving": self.roltype.omschrijving,
                    "omschrijvingGeneriek": self.roltype.omschrijving_generiek,
                    "registratiedatum": "2025-01-01T12:00:00Z",
                    "roltoelichting": "abc",
                    "roltype": f"http://testserver{self.roltype_url}",
                    "statussen": [],
                    "url": f"http://testserver{expected_rol_url}",
                    "uuid": str(rol.uuid),
                    "zaak": f"http://testserver{expected_zaak_url}",
                }
            ],
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_update_zaak_minimal(self):
        content = {
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_zaak_kenmerken_are_overwritten(self):
        ZaakKenmerkFactory(zaak=self.zaak, kenmerk="initial")

        content = {
            "zaak": {
                "kenmerken": [{"kenmerk": "blabla", "bron": "blabla"}],
            },
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(ZaakKenmerk.objects.count(), 1)

        self.assertEqual(response.data["zaak"]["kenmerken"][0]["kenmerk"], "blabla")

        self.assertEqual(ZaakKenmerk.objects.get().kenmerk, "blabla")
        self.assertEqual(ZaakKenmerk.objects.get().zaak, self.zaak)

    def test_zaak_kenmerken_are_kept(self):
        ZaakKenmerkFactory(zaak=self.zaak, kenmerk="initial")

        content = {"zaak": {}, "status": self.status}

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(ZaakKenmerk.objects.count(), 1)

        self.assertEqual(response.data["zaak"]["kenmerken"][0]["kenmerk"], "initial")

        self.assertEqual(ZaakKenmerk.objects.get().kenmerk, "initial")
        self.assertEqual(ZaakKenmerk.objects.get().zaak, self.zaak)

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

    def test_with_empty_status(self):
        content = {
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

    def test_with_eind_status(self):
        ResultaatFactory(
            zaak=self.zaak,
            resultaattype__brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )

        content = {
            "zaak": self.opschorting,
            "status": self.status
            | {"statustype": f"http://testserver{self.statustype_url_2}"},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["zaak"]["einddatum"], "2023-01-01")

        self.zaak.refresh_from_db()
        self.assertEqual(self.zaak.einddatum, datetime.date(2023, 1, 1))

    def test_rollen_are_added_and_existing_ones_are_kept(self):
        rol_1 = RolFactory(zaak=self.zaak, roltoelichting="1")
        rol_2 = RolFactory(zaak=self.zaak, roltoelichting="2")

        content = {
            "zaak": self.opschorting,
            "status": self.status,
            "rollen": [
                self.rol | {"roltoelichting": "3"},
                self.rol | {"roltoelichting": "4"},
            ],
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(response.data["rollen"]), 2)
        self.assertEqual(len(response.data["zaak"]["rollen"]), 4)

        self.assertEqual(Rol.objects.count(), 4)

        self.assertEqual(rol_1.zaak, self.zaak)
        rol_1_url = reverse(rol_1)

        self.assertEqual(rol_2.zaak, self.zaak)
        rol_2_url = reverse(rol_2)

        rol_3 = Rol.objects.get(roltoelichting=3)
        self.assertEqual(rol_3.zaak, self.zaak)
        self.assertEqual(rol_3.betrokkene, BETROKKENE)
        self.assertEqual(rol_3.roltype, self.roltype)
        rol_3_url = reverse(rol_3)

        rol_4 = Rol.objects.get(roltoelichting=4)
        self.assertEqual(rol_4.zaak, self.zaak)
        self.assertEqual(rol_4.betrokkene, BETROKKENE)
        self.assertEqual(rol_4.roltype, self.roltype)
        rol_4_url = reverse(rol_4)

        expected_zaak_url = reverse(self.zaak)

        response_data = response.json()
        expected_rollen = [
            {
                "afwijkendeNaamBetrokkene": "",
                "authenticatieContext": None,
                "beginGeldigheid": None,
                "betrokkene": "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                "betrokkeneIdentificatie": None,
                "betrokkeneType": "natuurlijk_persoon",
                "contactpersoonRol": {
                    "emailadres": "",
                    "functie": "",
                    "naam": "",
                    "telefoonnummer": "",
                },
                "eindeGeldigheid": None,
                "indicatieMachtiging": "",
                "omschrijving": self.roltype.omschrijving,
                "omschrijvingGeneriek": self.roltype.omschrijving_generiek,
                "registratiedatum": "2025-01-01T12:00:00Z",
                "roltoelichting": "3",
                "roltype": f"http://testserver{self.roltype_url}",
                "statussen": [],
                "url": f"http://testserver{rol_3_url}",
                "uuid": str(rol_3.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
            },
            {
                "afwijkendeNaamBetrokkene": "",
                "authenticatieContext": None,
                "beginGeldigheid": None,
                "betrokkene": "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                "betrokkeneIdentificatie": None,
                "betrokkeneType": "natuurlijk_persoon",
                "contactpersoonRol": {
                    "emailadres": "",
                    "functie": "",
                    "naam": "",
                    "telefoonnummer": "",
                },
                "eindeGeldigheid": None,
                "indicatieMachtiging": "",
                "omschrijving": self.roltype.omschrijving,
                "omschrijvingGeneriek": self.roltype.omschrijving_generiek,
                "registratiedatum": "2025-01-01T12:00:00Z",
                "roltoelichting": "4",
                "roltype": f"http://testserver{self.roltype_url}",
                "statussen": [],
                "url": f"http://testserver{rol_4_url}",
                "uuid": str(rol_4.uuid),
                "zaak": f"http://testserver{expected_zaak_url}",
            },
        ]
        self.assertEqual(response_data["rollen"], expected_rollen)

        self.assertEqual(
            response_data["zaak"]["rollen"],
            [
                f"http://testserver{rol_1_url}",
                f"http://testserver{rol_2_url}",
                f"http://testserver{rol_3_url}",
                f"http://testserver{rol_4_url}",
            ],
        )
