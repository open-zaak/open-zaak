# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..constants import IndicatieMachtiging
from ..models import (
    Adres,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    Rol,
    SubVerblijfBuitenland,
    Vestiging,
)
from .factories import RolFactory, StatusFactory, ZaakFactory
from .utils import get_operation_url, get_roltype_response, get_zaaktype_response

BETROKKENE = (
    "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


class RolTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    heeft_alle_autorisaties = True
    maxDiff = None

    @freeze_time("2018-01-01")
    def test_read_rol_np(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            afwijkende_naam_betrokkene="Another name",
            contactpersoon_rol_emailadres="test@mail.nl",
            contactpersoon_rol_functie="test function",
            contactpersoon_rol_naam="test name",
            contactpersoon_rol_telefoonnummer="061234567890",
        )
        naturlijkperson = NatuurlijkPersoon.objects.create(
            rol=rol, anp_identificatie="12345", inp_a_nummer="1234567890"
        )
        Adres.objects.create(
            natuurlijkpersoon=naturlijkperson,
            identificatie="123",
            postcode="1111",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test",
            huisnummer=1,
        )
        SubVerblijfBuitenland.objects.create(
            natuurlijkpersoon=naturlijkperson,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        status_ = StatusFactory.create(
            zaak=zaak, statustype__zaaktype=zaak.zaaktype, gezetdoor=rol
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "afwijkendeNaamBetrokkene": "Another name",
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.natuurlijk_persoon,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "inpBsn": "",
                    "anpIdentificatie": "12345",
                    "inpA_nummer": "1234567890",
                    "geslachtsnaam": "",
                    "voorvoegselGeslachtsnaam": "",
                    "voorletters": "",
                    "voornamen": "",
                    "geslachtsaanduiding": "",
                    "geboortedatum": "",
                    "verblijfsadres": {
                        "aoaIdentificatie": "123",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test",
                        "aoaPostcode": "1111",
                        "aoaHuisnummer": 1,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "inpLocatiebeschrijving": "",
                    },
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
                "contactpersoonRol": {
                    "emailadres": "test@mail.nl",
                    "functie": "test function",
                    "naam": "test name",
                    "telefoonnummer": "061234567890",
                },
                "statussen": [f"http://testserver{reverse(status_)}"],
                "authenticatieContext": None,
                "beginGeldigheid": None,
                "eindeGeldigheid": None,
            },
        )

    @freeze_time("2018-01-01")
    def test_read_rol_nnp(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
        )
        nietnaturlijkperson = NietNatuurlijkPersoon.objects.create(
            rol=rol, ann_identificatie="123456"
        )
        SubVerblijfBuitenland.objects.create(
            nietnatuurlijkpersoon=nietnaturlijkperson,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "afwijkendeNaamBetrokkene": "",
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "innNnpId": "",
                    "annIdentificatie": "123456",
                    "kvkNummer": "",
                    "statutaireNaam": "",
                    "innRechtsvorm": "",
                    "bezoekadres": "",
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
                "contactpersoonRol": {
                    "emailadres": "",
                    "functie": "",
                    "naam": "",
                    "telefoonnummer": "",
                },
                "authenticatieContext": None,
                "statussen": [],
                "beginGeldigheid": None,
                "eindeGeldigheid": None,
            },
        )

    @freeze_time("2018-01-01")
    def test_read_rol_vestiging(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.vestiging,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
        )
        vestiging = Vestiging.objects.create(
            rol=rol, vestigings_nummer="123456", kvk_nummer="12345678"
        )
        Adres.objects.create(
            vestiging=vestiging,
            identificatie="123",
            postcode="1111",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test",
            huisnummer=1,
        )
        SubVerblijfBuitenland.objects.create(
            vestiging=vestiging,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "afwijkendeNaamBetrokkene": "",
                "betrokkene": BETROKKENE,
                "betrokkeneType": str(RolTypes.vestiging),
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "vestigingsNummer": "123456",
                    "handelsnaam": [],
                    "kvkNummer": "12345678",
                    "verblijfsadres": {
                        "aoaIdentificatie": "123",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test",
                        "aoaPostcode": "1111",
                        "aoaHuisnummer": 1,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "inpLocatiebeschrijving": "",
                    },
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
                "contactpersoonRol": {
                    "emailadres": "",
                    "functie": "",
                    "naam": "",
                    "telefoonnummer": "",
                },
                "authenticatieContext": None,
                "statussen": [],
                "beginGeldigheid": None,
                "eindeGeldigheid": None,
            },
        )

    def test_create_rol_with_identificatie(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
            "betrokkeneIdentificatie": {
                "anpIdentificatie": "12345",
                "verblijfsadres": {
                    "aoaIdentificatie": "123",
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test",
                    "aoaPostcode": "1111",
                    "aoaHuisnummer": 1,
                },
                "subVerblijfBuitenland": {
                    "lndLandcode": "UK",
                    "lndLandnaam": "United Kingdom",
                    "subAdresBuitenland_1": "some uk adres",
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(NatuurlijkPersoon.objects.count(), 1)
        self.assertEqual(NietNatuurlijkPersoon.objects.count(), 0)

        rol = Rol.objects.get()
        natuurlijk_persoon = NatuurlijkPersoon.objects.get()
        adres = Adres.objects.get()
        verblijf_buitenland = SubVerblijfBuitenland.objects.get()

        self.assertEqual(rol.natuurlijkpersoon, natuurlijk_persoon)
        self.assertEqual(natuurlijk_persoon.anp_identificatie, "12345")
        self.assertEqual(natuurlijk_persoon.verblijfsadres, adres)
        self.assertEqual(adres.identificatie, "123")
        self.assertEqual(
            natuurlijk_persoon.sub_verblijf_buitenland, verblijf_buitenland
        )
        self.assertEqual(verblijf_buitenland.lnd_landcode, "UK")

    def test_create_rol_without_identificatie(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(NatuurlijkPersoon.objects.count(), 0)

        rol = Rol.objects.get()

        self.assertEqual(rol.betrokkene, BETROKKENE)

    def test_create_rol_fail_validation(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")

        self.assertEqual(validation_error["code"], "invalid-betrokkene")

    @freeze_time("2018-01-01")
    def test_filter_rol_np_bsn(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        NatuurlijkPersoon.objects.create(
            rol=rol, inp_bsn="183068142", inp_a_nummer="1234567890"
        )

        rol_2 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        NatuurlijkPersoon.objects.create(
            rol=rol_2, inp_bsn="650237481", inp_a_nummer="2234567890"
        )

        rol_3 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.vestiging,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        Vestiging.objects.create(rol=rol_3, vestigings_nummer="183068142")

        url = get_operation_url("rol_list", uuid=rol.uuid)

        response = self.client.get(
            url, {"betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "183068142"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["betrokkeneIdentificatie"]["inpBsn"], "183068142")

    def test_create_rol_omschrijving_length_100(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype, omschrijving="a" * 100)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
            "betrokkeneIdentificatie": {
                "anpIdentificatie": "12345",
                "verblijfsadres": {
                    "aoaIdentificatie": "123",
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test",
                    "aoaPostcode": "1111",
                    "aoaHuisnummer": 1,
                },
                "subVerblijfBuitenland": {
                    "lndLandcode": "UK",
                    "lndLandnaam": "United Kingdom",
                    "subAdresBuitenland_1": "some uk adres",
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()
        self.assertEqual(rol.omschrijving, "a" * 100)

    def test_filter_rol_betrokkene_identificatie_organisatorische_eenheid(self):
        zaak = ZaakFactory.create()
        rol1 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        OrganisatorischeEenheid.objects.create(
            rol=rol1, identificatie="oor", naam="Ruimte"
        )
        rol2 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        OrganisatorischeEenheid.objects.create(
            rol=rol2, identificatie="pbz", naam="Publiekszaken"
        )

        url = get_operation_url("rol_list")

        with self.subTest(case="new parameter"):
            response = self.client.get(
                url,
                {
                    "betrokkeneIdentificatie__organisatorischeEenheid__identificatie": "pbz"
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            data = response.json()["results"]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["betrokkeneIdentificatie"]["identificatie"], "pbz")

        with self.subTest(case="old parameter"):
            response = self.client.get(
                url, {"betrokkeneIdentificatie__vestiging__identificatie": "pbz"}
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            err = get_validation_errors(response, "nonFieldErrors")
            self.assertEqual(err["code"], "unknown-parameters")

    def test_create_rol_with_contactpersoon(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
            "contactpersoonRol": {
                "emailadres": "test@mail.nl",
                "functie": "test function",
                "naam": "test name",
                "telefoonnummer": "061234567890",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()

        self.assertEqual(rol.betrokkene, BETROKKENE)
        self.assertEqual(rol.contactpersoon_rol_emailadres, "test@mail.nl")
        self.assertEqual(rol.contactpersoon_rol_functie, "test function")
        self.assertEqual(rol.contactpersoon_rol_naam, "test name")
        self.assertEqual(rol.contactpersoon_rol_telefoonnummer, "061234567890")

    def test_create_rol_with_empty_aoaIdentificatie(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
            "betrokkeneIdentificatie": {
                "anpIdentificatie": "12345",
                "verblijfsadres": {
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test",
                    "aoaPostcode": "1111",
                    "aoaHuisnummer": 1,
                },
                "subVerblijfBuitenland": {
                    "lndLandcode": "UK",
                    "lndLandnaam": "United Kingdom",
                    "subAdresBuitenland_1": "some uk adres",
                },
            },
        }

        # field is still required
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(
            response, "betrokkeneIdentificatie.verblijfsadres.aoaIdentificatie"
        )
        self.assertEqual(validation_error["code"], "required")

        data["betrokkeneIdentificatie"]["verblijfsadres"]["aoaIdentificatie"] = ""
        # allowed to be empty
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        adres = Adres.objects.get()
        self.assertEqual(adres.identificatie, "")

    def test_pagination_pagesize_param(self):
        RolFactory.create_batch(10)
        url = get_operation_url("rol_list")

        response = self.client.get(url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(data["next"], f"http://testserver{url}?page=2&pageSize=5")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class RolCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("rol_create")

    def test_create_external_roltype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        roltype = "https://externe.catalogus.nl/api/v1/roltypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = reverse(zaak)

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(roltype, json=get_roltype_response(roltype, zaaktype))

            response = self.client.post(
                self.list_url,
                {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": roltype,
                    "roltoelichting": "awerw",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_roltype_fail_bad_url(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.post(
            self.list_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.natuurlijk_persoon,
                "roltype": "abcd",
                "roltoelichting": "awerw",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "roltype")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_roltype_fail_not_json_url(self):
        ServiceFactory.create(api_root="http://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                self.list_url,
                {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": "http://example.com/",
                    "roltoelichting": "awerw",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "roltype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_roltype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        roltype = "https://externe.catalogus.nl/api/v1/roltypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = reverse(zaak)

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(roltype, json={"url": roltype, "zaaktype": zaaktype})

            response = self.client.post(
                self.list_url,
                {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": roltype,
                    "roltoelichting": "awerw",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "roltype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_roltype_fail_zaaktype_mismatch(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        roltype = "https://externe.catalogus.nl/api/v1/roltypen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype1)
        zaak_url = reverse(zaak)

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype1, json=get_zaaktype_response(catalogus, zaaktype1))
            m.get(zaaktype2, json=get_zaaktype_response(catalogus, zaaktype2))
            m.get(roltype, json=get_roltype_response(roltype, zaaktype2))

            response = self.client.post(
                self.list_url,
                {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": roltype,
                    "roltoelichting": "awerw",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_create_external_roltype_fail_unknown_service(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.post(
            self.list_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.natuurlijk_persoon,
                "roltype": "https://other-externe.catalogus.nl/api/v1/roltypen/1",
                "roltoelichting": "awerw",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "roltype")
        self.assertEqual(error["code"], "unknown-service")
