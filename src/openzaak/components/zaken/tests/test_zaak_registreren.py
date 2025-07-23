from datetime import date

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    ComponentTypes,
    RelatieAarden,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from openzaak.components.zaken.models import (
    Rol,
    Status,
    Zaak,
    ZaakInformatieObject,
    ZaakObject,
)
from openzaak.components.zaken.tests.test_rol import BETROKKENE
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
@override_settings(
    OPENZAAK_DOMAIN="testserver", LINK_FETCHER="vng_api_common.mocks.link_fetcher_200"
)
class ZaakRegistrerenAuthTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("registreerzaak-list")
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

        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        cls.zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=cls.informatieobjecttype.catalogus
        )
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=cls.zaaktype, informatieobjecttype=cls.informatieobjecttype
        )

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
            scopes=[SCOPE_ZAKEN_CREATE] + scopes,
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

        informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        informatieobject_url = reverse(informatieobject)

        self.content = {
            "zaak": {
                "zaaktype": self.zaaktype_url,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
                "toelichting": "toelichting",
            },
            "rollen": [
                {
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": self.roltype_url,
                    "roltoelichting": "awerw",
                }
            ],
            "zaakinformatieobjecten": [
                {
                    "informatieobject": f"http://testserver{informatieobject_url}",
                    "titel": "string",
                    "beschrijving": "string",
                    "vernietigingsdatum": "2019-08-24T14:15:22Z",
                }
            ],
            "zaakobjecten": [
                {
                    "objectType": ZaakobjectTypes.overige,
                    "objectTypeOverige": "test",
                    "relatieomschrijving": "test",
                    "objectIdentificatie": {"overigeData": {"someField": "some value"}},
                }
            ],
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2023-01-01T00:00:00",
            },
        }

    def test_registreer_zaak(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN])

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_registreer_zaak_without_update_scope(self):
        self._add_zaken_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_registreer_zaak_with_force_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN])

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_registreer_zaak_no_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_registreer_zaak_no_zaaktype_in_auth(self):
        self._add_zaken_auth(zaaktype="", scopes=[SCOPE_ZAKEN_BIJWERKEN])

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_zaak_with_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_zaak_with_end_status(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_BIJWERKEN])

        content = self.content.copy()

        content["status"]["statustype"] = self.check_for_instance(self.end_statustype)

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "resultaat-does-not-exist")


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class ZaakRegistrerenValidationTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("registreerzaak-list")
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        self.zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=self.informatieobjecttype.catalogus
        )
        self.zaaktype_url = reverse(self.zaaktype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=self.zaaktype, informatieobjecttype=self.informatieobjecttype
        )

        self.roltype = RolTypeFactory(zaaktype=self.zaaktype)
        self.roltype_url = reverse(self.roltype)

        self.statustype_1 = StatusTypeFactory.create(zaaktype=self.zaaktype)
        self.statustype_url = reverse(self.statustype_1)

        self.statustype_2 = StatusTypeFactory.create(zaaktype=self.zaaktype)

        self.informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        self.informatieobject_url = reverse(self.informatieobject)

        self.zaak = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
            "toelichting": "toelichting",
        }

        self.rol = {
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "awerw",
        }

        self.zio = {
            "informatieobject": f"http://testserver{self.informatieobject_url}",
            "titel": "string",
            "beschrijving": "string",
            "vernietigingsdatum": "2019-08-24T14:15:22Z",
        }

        self.zaakobject = {
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverige": "test",
            "relatieomschrijving": "test",
            "objectIdentificatie": {"overigeData": {"someField": "some value"}},
        }

        self.status = {
            "statustype": f"http://testserver{self.statustype_url}",
            "datumStatusGezet": "2023-01-01T00:00:00",
        }

    def test_registreer_zaak(self):
        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "zaakinformatieobjecten": [self.zio],
            "zaakobjecten": [self.zaakobject],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()

        self.assertEqual(
            zaak.vertrouwelijkheidaanduiding, VertrouwelijkheidsAanduiding.openbaar
        )
        self.assertEqual(zaak.zaaktype, self.zaaktype)
        self.assertEqual(zaak.bronorganisatie, "517439943")
        self.assertEqual(zaak.verantwoordelijke_organisatie, "517439943")
        self.assertEqual(zaak.startdatum, date(2018, 6, 11))
        self.assertEqual(zaak.registratiedatum, date(2018, 6, 11))
        self.assertEqual(zaak.toelichting, "toelichting")
        self.assertIsNone(zaak.einddatum)

        rol = Rol.objects.get()

        self.assertEqual(rol.zaak, zaak)
        self.assertEqual(rol.betrokkene, BETROKKENE)
        self.assertEqual(rol.roltype, self.roltype)

        zio = ZaakInformatieObject.objects.get()

        self.assertEqual(zio.zaak, zaak)
        self.assertEqual(
            zio.vernietigingsdatum.isoformat(), "2019-08-24T14:15:22+00:00"
        )
        self.assertEqual(zio.titel, "string")
        self.assertEqual(zio.informatieobject, self.informatieobject.canonical)

        zaakobject = ZaakObject.objects.get()

        self.assertEqual(zaakobject.object_type, ZaakobjectTypes.overige)
        self.assertEqual(zaakobject.zaak, zaak)
        self.assertEqual(zaakobject.overige.overige_data, {"some_field": "some value"})

        _status = Status.objects.get()

        self.assertEqual(_status.zaak, zaak)
        self.assertEqual(_status.statustype, self.statustype_1)
        self.assertEqual(
            _status.datum_status_gezet.isoformat(), "2023-01-01T00:00:00+00:00"
        )

        expected_zaak_url = reverse(zaak)
        expected_rol_url = reverse(rol)
        expected_zio_url = reverse(zio)
        expected_zaakobject_url = reverse(zaakobject)
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
                "identificatie": "ZAAK-2018-0000000001",
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
                "registratiedatum": "2018-06-11",
                "relevanteAndereZaken": [],
                "resultaat": None,
                "rollen": [
                    f"http://testserver{expected_rol_url}",
                ],
                "selectielijstklasse": "",
                "startdatum": "2018-06-11",
                "startdatumBewaartermijn": None,
                "status": f"http://testserver{expected_status_url}",
                "toelichting": "toelichting",
                "uiterlijkeEinddatumAfdoening": None,
                "url": f"http://testserver{expected_zaak_url}",
                "uuid": str(zaak.uuid),
                "verantwoordelijkeOrganisatie": "517439943",
                "verlenging": None,
                "vertrouwelijkheidaanduiding": "openbaar",
                "zaakgeometrie": None,
                "zaakinformatieobjecten": [
                    f"http://testserver{expected_zio_url}",
                ],
                "zaakobjecten": [
                    f"http://testserver{expected_zaakobject_url}",
                ],
                "zaaktype": f"http://testserver{self.zaaktype_url}",
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
                    "roltoelichting": "awerw",
                    "roltype": f"http://testserver{self.roltype_url}",
                    "statussen": [],
                    "url": f"http://testserver{expected_rol_url}",
                    "uuid": str(rol.uuid),
                    "zaak": f"http://testserver{expected_zaak_url}",
                }
            ],
            "zaakinformatieobjecten": [
                {
                    "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
                    "beschrijving": "string",
                    "informatieobject": f"http://testserver{self.informatieobject_url}",
                    "registratiedatum": "2025-01-01T12:00:00Z",
                    "status": None,
                    "titel": "string",
                    "url": f"http://testserver{expected_zio_url}",
                    "uuid": str(zio.uuid),
                    "vernietigingsdatum": "2019-08-24T14:15:22Z",
                    "zaak": f"http://testserver{expected_zaak_url}",
                }
            ],
            "zaakobjecten": [
                {
                    "object": "",
                    "objectType": "overige",
                    "objectTypeOverige": "test",
                    "objectTypeOverigeDefinitie": None,
                    "relatieomschrijving": "test",
                    "url": f"http://testserver{expected_zaakobject_url}",
                    "uuid": str(zaakobject.uuid),
                    "zaak": f"http://testserver{expected_zaak_url}",
                    "zaakobjecttype": None,
                    "objectIdentificatie": {"overigeData": {"someField": "some value"}},
                }
            ],
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

    def test_register_zaak_minimal(self):
        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_zaak_missing_related_objects(self):
        content = {
            "zaak": self.zaak,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        rol_error = get_validation_errors(response, "rollen")
        self.assertEqual(rol_error["code"], "required")

        status_error = get_validation_errors(response, "status")
        self.assertEqual(status_error["code"], "required")

    def test_zaaktype_statustype_relation(self):
        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "status": self.status
            | {"statustype": self.check_for_instance(StatusTypeFactory.create())},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_zaaktype_roltype_relation(self):
        content = {
            "zaak": self.zaak,
            "rollen": [
                self.rol | {"roltype": self.check_for_instance(RolTypeFactory.create())}
            ],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_no_zaaktypeinformatieobjecttype(self):
        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "zaakinformatieobjecten": [
                self.zio
                | {
                    "informatieobject": self.check_for_instance(
                        EnkelvoudigInformatieObjectFactory.create()
                    )
                }
            ],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_register_zaak_with_end_status(self):
        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "zaakinformatieobjecten": [self.zio],
            "zaakobjecten": [self.zaakobject],
            "status": self.status
            | {"statustype": self.check_for_instance(self.statustype_2)},
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_register_zaak_with_zaakobject_not_overig_and_object_type_overige(self):
        self.zaakobject.pop("objectTypeOverige")

        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "zaakinformatieobjecten": [self.zio],
            "zaakobjecten": [self.zaakobject],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "missing-object-type-overige")

    def test_register_zaak_with_rol_without_betrokkene(self):
        self.rol.pop("betrokkene")

        content = {
            "zaak": self.zaak,
            "rollen": [self.rol],
            "zaakinformatieobjecten": [self.zio],
            "zaakobjecten": [self.zaakobject],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-betrokkene")

    def test_with_other_rol_and_zaakobject_poly_type(self):
        content = {
            "zaak": self.zaak,
            "rollen": [
                {
                    "betrokkeneIdentificatie": {
                        "kvkNummer": "12345678",
                        "vestigingsNummer": "123456789012",
                    },
                    "betrokkene_type": RolTypes.vestiging,
                    "roltype": f"http://testserver{self.roltype_url}",
                    "roltoelichting": "awerw",
                }
            ],
            "zaakinformatieobjecten": [self.zio],
            "zaakobjecten": [
                {
                    "objectType": ZaakobjectTypes.medewerker,
                    "objectIdentificatie": {
                        "identificatie": "123456",
                        "achternaam": "Jong",
                        "voorletters": "J",
                        "voorvoegselAchternaam": "van",
                    },
                }
            ],
            "status": self.status,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response_data = response.json()
        betrokkene_identificatie = {
            "handelsnaam": [],
            "kvkNummer": "12345678",
            "subVerblijfBuitenland": None,
            "verblijfsadres": None,
            "vestigingsNummer": "123456789012",
        }

        self.assertCountEqual(response_data["rollen"][0]["betrokkeneType"], "vestiging")
        self.assertCountEqual(
            response_data["rollen"][0]["betrokkeneIdentificatie"],
            betrokkene_identificatie,
        )

        object_identificatie = {
            "achternaam": "Jong",
            "identificatie": "123456",
            "voorletters": "J",
            "voorvoegselAchternaam": "van",
        }

        self.assertCountEqual(
            response_data["zaakobjecten"][0]["objectType"], "medewerker"
        )
        self.assertCountEqual(
            response_data["zaakobjecten"][0]["objectIdentificatie"],
            object_identificatie,
        )
