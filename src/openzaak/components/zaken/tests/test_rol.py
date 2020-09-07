# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from ..constants import IndicatieMachtiging
from ..models import (
    Adres,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    Rol,
    SubVerblijfBuitenland,
    Vestiging,
)
from .factories import RolFactory, ZaakFactory
from .utils import get_operation_url, get_roltype_response, get_zaaktype_response

BETROKKENE = (
    "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


class RolTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    heeft_alle_autorisaties = True

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
        vestiging = Vestiging.objects.create(rol=rol, vestigings_nummer="123456")
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
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.vestiging,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "vestigingsNummer": "123456",
                    "handelsnaam": [],
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

        with requests_mock.Mocker(real_http=True) as m:
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
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.post(
            self.list_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.natuurlijk_persoon,
                "roltype": "http://example.com",
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

        with requests_mock.Mocker(real_http=True) as m:
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

        with requests_mock.Mocker(real_http=True) as m:
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
