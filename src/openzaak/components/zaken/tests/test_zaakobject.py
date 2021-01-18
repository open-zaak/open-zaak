# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ZaakobjectTypes
from vng_api_common.tests import get_validation_errors
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.bag.tests import mock_pand_get
from openzaak.utils.tests import JWTAuthMixin

from ..models import (
    Adres,
    Huishouden,
    KadastraleOnroerendeZaak,
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    Overige,
    TerreinGebouwdObject,
    WozDeelobject,
    WozObject,
    WozWaarde,
    ZaakObject,
    ZakelijkRecht,
    ZakelijkRechtHeeftAlsGerechtigde,
)
from .factories import ZaakFactory, ZaakObjectFactory
from .utils import get_operation_url

OBJECT = "http://example.org/api/zaakobjecten/8768c581-2817-4fe5-933d-37af92d819dd"


class ZaakObjectBaseTestCase(JWTAuthMixin, APITestCase):
    """
    general cases for zaakobject without object_identificatie
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_without_identificatie(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object=OBJECT, object_type=ZaakobjectTypes.besluit
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": OBJECT,
                "objectType": ZaakobjectTypes.besluit,
                "objectTypeOverige": "",
                "relatieomschrijving": "",
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject_without_identificatie(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.besluit,
            "relatieomschrijving": "test",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()

        self.assertEqual(zaakobject.object, OBJECT)

    def test_create_rol_fail_validation(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.besluit,
            "relatieomschrijving": "test",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "invalid-zaakobject")


class ZaakObjectAdresTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism with simple child object Adres
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_adres(self):

        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.adres
        )
        Adres.objects.create(
            zaakobject=zaakobject,
            identificatie="123456",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer=1,
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.adres,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "identificatie": "123456",
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test space",
                    "huisnummer": 1,
                    "huisletter": "",
                    "huisnummertoevoeging": "",
                    "postcode": "",
                },
            },
        )

    def test_create_zaakobject_adres(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "identificatie": "123456",
                "wplWoonplaatsNaam": "test city",
                "gorOpenbareRuimteNaam": "test space",
                "huisnummer": 1,
                "huisletter": "",
                "huisnummertoevoeging": "",
                "postcode": "",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(Adres.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        adres = Adres.objects.get()

        self.assertEqual(zaakobject.adres, adres)
        self.assertEqual(adres.identificatie, "123456")


class ZaakObjectHuishoudenTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for Huishouden object with nesting
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_huishouden(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.huishouden
        )

        huishouden = Huishouden.objects.create(zaakobject=zaakobject, nummer="123456")
        terreingebouwdobject = TerreinGebouwdObject.objects.create(
            huishouden=huishouden, identificatie="1"
        )
        Adres.objects.create(
            terreingebouwdobject=terreingebouwdobject,
            num_identificatie="1",
            identificatie="a",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer="11",
            locatie_aanduiding="test",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.huishouden,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "nummer": "123456",
                    "isGehuisvestIn": {
                        "identificatie": "1",
                        "adresAanduidingGrp": {
                            "numIdentificatie": "1",
                            "oaoIdentificatie": "a",
                            "wplWoonplaatsNaam": "test city",
                            "gorOpenbareRuimteNaam": "test space",
                            "aoaPostcode": "",
                            "aoaHuisnummer": 11,
                            "aoaHuisletter": "",
                            "aoaHuisnummertoevoeging": "",
                            "ogoLocatieAanduiding": "test",
                        },
                    },
                },
            },
        )

    def test_create_zaakobject_huishouden(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.huishouden,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "nummer": "123456",
                "isGehuisvestIn": {
                    "identificatie": "1",
                    "adresAanduidingGrp": {
                        "numIdentificatie": "1",
                        "oaoIdentificatie": "a",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test space",
                        "aoaPostcode": "1010",
                        "aoaHuisnummer": 11,
                        "aoaHuisletter": "a",
                        "aoaHuisnummertoevoeging": "test",
                        "ogoLocatieAanduiding": "test",
                    },
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(Huishouden.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        huishouden = Huishouden.objects.get()

        self.assertEqual(zaakobject.huishouden, huishouden)
        self.assertEqual(huishouden.nummer, "123456")
        self.assertEqual(
            huishouden.is_gehuisvest_in.adres_aanduiding_grp.identificatie, "a"
        )


class ZaakObjectMedewerkerTestCase(JWTAuthMixin, APITestCase):
    """
    check polyphormism for Rol-related object Medewerker
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_medewerker(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.medewerker
        )
        Medewerker.objects.create(
            zaakobject=zaakobject,
            identificatie="123456",
            achternaam="Jong",
            voorletters="J",
            voorvoegsel_achternaam="van",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.medewerker,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "identificatie": "123456",
                    "achternaam": "Jong",
                    "voorletters": "J",
                    "voorvoegselAchternaam": "van",
                },
            },
        )

    def test_create_zaakobject_medewerker(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.medewerker,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "identificatie": "123456",
                "achternaam": "Jong",
                "voorletters": "J",
                "voorvoegselAchternaam": "van",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(Medewerker.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        medewerker = Medewerker.objects.get()

        self.assertEqual(zaakobject.medewerker, medewerker)
        self.assertEqual(medewerker.identificatie, "123456")


class ZaakObjectTerreinGebouwdObjectTestCase(JWTAuthMixin, APITestCase):
    """
    check polyphormism for object TerreinGebouwdObject with GegevensGroep
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_terreinGebouwdObject(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.terrein_gebouwd_object
        )

        terreingebouwdobject = TerreinGebouwdObject.objects.create(
            zaakobject=zaakobject, identificatie="12345"
        )
        Adres.objects.create(
            terreingebouwdobject=terreingebouwdobject,
            num_identificatie="1",
            identificatie="123",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer="11",
            locatie_aanduiding="test",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.terrein_gebouwd_object,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "identificatie": "12345",
                    "adresAanduidingGrp": {
                        "numIdentificatie": "1",
                        "oaoIdentificatie": "123",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test space",
                        "aoaPostcode": "",
                        "aoaHuisnummer": 11,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "ogoLocatieAanduiding": "test",
                    },
                },
            },
        )

    def test_create_zaakobject_terreinGebouwdObject(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.terrein_gebouwd_object,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "identificatie": "12345",
                "adresAanduidingGrp": {
                    "numIdentificatie": "1",
                    "oaoIdentificatie": "a",
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test space",
                    "aoaPostcode": "1010",
                    "aoaHuisnummer": 11,
                    "aoaHuisletter": "a",
                    "aoaHuisnummertoevoeging": "test",
                    "ogoLocatieAanduiding": "test",
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(TerreinGebouwdObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        terrein_gebouwd = TerreinGebouwdObject.objects.get()
        adres = Adres.objects.get()

        self.assertEqual(zaakobject.terreingebouwdobject, terrein_gebouwd)
        self.assertEqual(terrein_gebouwd.identificatie, "12345")
        self.assertEqual(terrein_gebouwd.adres_aanduiding_grp, adres)
        self.assertEqual(adres.identificatie, "a")


class ZaakObjectWozObjectTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for WozObject object with GegevensGroep
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_wozObject(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.woz_object
        )

        wozobject = WozObject.objects.create(
            zaakobject=zaakobject, woz_object_nummer="12345"
        )
        Adres.objects.create(
            wozobject=wozobject,
            identificatie="a",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer="11",
            locatie_omschrijving="test",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.woz_object,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "wozObjectNummer": "12345",
                    "aanduidingWozObject": {
                        "aoaIdentificatie": "a",
                        "wplWoonplaatsNaam": "test city",
                        "aoaPostcode": "",
                        "gorOpenbareRuimteNaam": "test space",
                        "aoaHuisnummer": 11,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "locatieOmschrijving": "test",
                    },
                },
            },
        )

    def test_create_zaakobject_wozObject(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.woz_object,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "wozObjectNummer": "12345",
                "aanduidingWozObject": {
                    "aoaIdentificatie": "a",
                    "wplWoonplaatsNaam": "test city",
                    "aoaPostcode": "",
                    "gorOpenbareRuimteNaam": "test space",
                    "aoaHuisnummer": 11,
                    "aoaHuisletter": "",
                    "aoaHuisnummertoevoeging": "",
                    "locatieOmschrijving": "test",
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(WozObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        wozobject = WozObject.objects.get()
        adres = Adres.objects.get()

        self.assertEqual(zaakobject.wozobject, wozobject)
        self.assertEqual(wozobject.woz_object_nummer, "12345")
        self.assertEqual(wozobject.aanduiding_woz_object, adres)
        self.assertEqual(adres.identificatie, "a")


class ZaakObjectWozDeelobjectTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for WozDeelobject object with nesting
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_wozDeelObject(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.woz_deelobject
        )

        woz_deel_object = WozDeelobject.objects.create(
            zaakobject=zaakobject, nummer_woz_deel_object="12345"
        )

        wozobject = WozObject.objects.create(
            woz_deelobject=woz_deel_object, woz_object_nummer="1"
        )
        Adres.objects.create(
            wozobject=wozobject,
            identificatie="a",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer="11",
            locatie_omschrijving="test",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.woz_deelobject,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "nummerWozDeelObject": "12345",
                    "isOnderdeelVan": {
                        "wozObjectNummer": "1",
                        "aanduidingWozObject": {
                            "aoaIdentificatie": "a",
                            "wplWoonplaatsNaam": "test city",
                            "aoaPostcode": "",
                            "gorOpenbareRuimteNaam": "test space",
                            "aoaHuisnummer": 11,
                            "aoaHuisletter": "",
                            "aoaHuisnummertoevoeging": "",
                            "locatieOmschrijving": "test",
                        },
                    },
                },
            },
        )

    def test_create_zaakobject_wozDeelObject(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.woz_deelobject,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "nummerWozDeelObject": "12345",
                "isOnderdeelVan": {
                    "wozObjectNummer": "1",
                    "aanduidingWozObject": {
                        "aoaIdentificatie": "a",
                        "wplWoonplaatsNaam": "test city",
                        "aoaPostcode": "",
                        "gorOpenbareRuimteNaam": "test space",
                        "aoaHuisnummer": 11,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "locatieOmschrijving": "test",
                    },
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(WozDeelobject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        wozdeelobject = WozDeelobject.objects.get()
        adres = Adres.objects.get()

        self.assertEqual(zaakobject.wozdeelobject, wozdeelobject)
        self.assertEqual(wozdeelobject.nummer_woz_deel_object, "12345")
        self.assertEqual(wozdeelobject.is_onderdeel_van.aanduiding_woz_object, adres)
        self.assertEqual(adres.identificatie, "a")


class ZaakObjectWozWaardeTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for WozWaarde object with nesting
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_wozWaarde(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.woz_waarde
        )

        woz_warde = WozWaarde.objects.create(
            zaakobject=zaakobject, waardepeildatum="2019"
        )

        wozobject = WozObject.objects.create(woz_warde=woz_warde, woz_object_nummer="1")
        Adres.objects.create(
            wozobject=wozobject,
            identificatie="a",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test space",
            huisnummer="11",
            locatie_omschrijving="test",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.woz_waarde,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "waardepeildatum": "2019",
                    "isVoor": {
                        "wozObjectNummer": "1",
                        "aanduidingWozObject": {
                            "aoaIdentificatie": "a",
                            "wplWoonplaatsNaam": "test city",
                            "aoaPostcode": "",
                            "gorOpenbareRuimteNaam": "test space",
                            "aoaHuisnummer": 11,
                            "aoaHuisletter": "",
                            "aoaHuisnummertoevoeging": "",
                            "locatieOmschrijving": "test",
                        },
                    },
                },
            },
        )

    def test_create_zaakobject_wozWaarde(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.woz_waarde,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "waardepeildatum": "2019",
                "isVoor": {
                    "wozObjectNummer": "1",
                    "aanduidingWozObject": {
                        "aoaIdentificatie": "a",
                        "wplWoonplaatsNaam": "test city",
                        "aoaPostcode": "",
                        "gorOpenbareRuimteNaam": "test space",
                        "aoaHuisnummer": 11,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "locatieOmschrijving": "test",
                    },
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(WozWaarde.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        wozwaarde = WozWaarde.objects.get()
        adres = Adres.objects.get()

        self.assertEqual(zaakobject.wozwaarde, wozwaarde)
        self.assertEqual(wozwaarde.waardepeildatum, "2019")
        self.assertEqual(wozwaarde.is_voor.aanduiding_woz_object, adres)
        self.assertEqual(adres.identificatie, "a")


class ZaakObjectZakelijkRechtTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for ZakelijkRecht object with nesting
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_zakelijkRecht(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.zakelijk_recht
        )

        zakelijk_recht = ZakelijkRecht.objects.create(
            zaakobject=zaakobject, identificatie="12345", avg_aard="test"
        )

        KadastraleOnroerendeZaak.objects.create(
            zakelijk_recht=zakelijk_recht,
            kadastrale_identificatie="1",
            kadastrale_aanduiding="test",
        )

        heeft_als_gerechtigde = ZakelijkRechtHeeftAlsGerechtigde.objects.create(
            zakelijk_recht=zakelijk_recht
        )
        NatuurlijkPersoon.objects.create(
            zakelijk_rechtHeeft_als_gerechtigde=heeft_als_gerechtigde,
            anp_identificatie="12345",
            inp_a_nummer="1234567890",
        )
        NietNatuurlijkPersoon.objects.create(
            zakelijk_rechtHeeft_als_gerechtigde=heeft_als_gerechtigde,
            ann_identificatie="123456",
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.zakelijk_recht,
                "objectTypeOverige": "",
                "objectIdentificatie": {
                    "identificatie": "12345",
                    "avgAard": "test",
                    "heeftBetrekkingOp": {
                        "kadastraleIdentificatie": "1",
                        "kadastraleAanduiding": "test",
                    },
                    "heeftAlsGerechtigde": {
                        "natuurlijkPersoon": {
                            "inpBsn": "",
                            "anpIdentificatie": "12345",
                            "inpA_nummer": "1234567890",
                            "geslachtsnaam": "",
                            "voorvoegselGeslachtsnaam": "",
                            "voorletters": "",
                            "voornamen": "",
                            "geslachtsaanduiding": "",
                            "geboortedatum": "",
                            "verblijfsadres": None,
                            "subVerblijfBuitenland": None,
                        },
                        "nietNatuurlijkPersoon": {
                            "innNnpId": "",
                            "annIdentificatie": "123456",
                            "statutaireNaam": "",
                            "innRechtsvorm": "",
                            "bezoekadres": "",
                            "subVerblijfBuitenland": None,
                        },
                    },
                },
            },
        )

    def test_create_zaakobject_zakelijkRecht(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.zakelijk_recht,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
            "objectIdentificatie": {
                "identificatie": "1111",
                "avgAard": "test",
                "heeftBetrekkingOp": {
                    "kadastraleIdentificatie": "1",
                    "kadastraleAanduiding": "test",
                },
                "heeftAlsGerechtigde": {
                    "natuurlijkPersoon": {
                        "inpBsn": "",
                        "anpIdentificatie": "1234",
                        "inpA_nummer": "1234567890",
                    },
                    "nietNatuurlijkPersoon": {
                        "innNnpId": "",
                        "annIdentificatie": "123456",
                    },
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(ZakelijkRecht.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        zakelijkrecht = ZakelijkRecht.objects.get()

        self.assertEqual(zaakobject.zakelijkrecht, zakelijkrecht)
        self.assertEqual(zakelijkrecht.identificatie, "1111")
        self.assertEqual(
            zakelijkrecht.heeft_betrekking_op.kadastrale_identificatie, "1"
        )
        self.assertEqual(
            zakelijkrecht.heeft_als_gerechtigde.natuurlijkpersoon.anp_identificatie,
            "1234",
        )
        self.assertEqual(
            zakelijkrecht.heeft_als_gerechtigde.nietnatuurlijkpersoon.ann_identificatie,
            "123456",
        )


class ZaakObjectOverigeTestCase(JWTAuthMixin, APITestCase):
    """
    check polymorphism for Overige object with JSON field
    """

    heeft_alle_autorisaties = True

    def test_read_zaakobject_overige(self):

        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak, object="", object_type=ZaakobjectTypes.overige
        )
        Overige.objects.create(
            zaakobject=zaakobject, overige_data={"some_field": "some value"}
        )

        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": "",
                "relatieomschrijving": "",
                "objectType": ZaakobjectTypes.overige,
                "objectTypeOverige": "",
                "objectIdentificatie": {"overigeData": {"someField": "some value"}},
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject_overige_with_url(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverige": "test",
            "relatieomschrijving": "test",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(Overige.objects.count(), 0)

    def test_create_zaakobject_overige_with_data(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverige": "test",
            "relatieomschrijving": "test",
            "objectIdentificatie": {"overigeData": {"someField": "some value"}},
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(ZaakObject.objects.count(), 1)
        self.assertEqual(Overige.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        overige = Overige.objects.get()

        self.assertEqual(zaakobject.overige, overige)
        self.assertEqual(overige.overige_data, {"some_field": "some value"})

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject_overige_without_type(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.overige,
            "relatieomschrijving": "test",
            "objectTypeOverige": "",
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "missing-object-type-overige")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject_with_overige_type(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "objectTypeOverige": "test",
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-object-type-overige-usage")


@tag("bag")
class ZaakObjectBagPandTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @requests_mock.Mocker()
    def test_create_zaakobject_bag_auth(self, m):
        mock_pand_get(
            m,
            "https://bag.basisregistraties.overheid.nl/api/v1/panden/0344100000011708?geldigOp=2020-03-04",
        )
        Service.objects.create(
            api_root="https://bag.basisregistraties.overheid.nl/api/v1",
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            label="BAG",
            header_key="X-Api-Key",
            header_value="foo",
        )

        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.pand,
            "relatieomschrijving": "",
            "object": "https://bag.basisregistraties.overheid.nl/api/v1/panden/0344100000011708?geldigOp=2020-03-04",
        }

        resp = self.client.post(url, data)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(
            m.last_request.url,
            "https://bag.basisregistraties.overheid.nl/api/v1/panden/0344100000011708?geldigOp=2020-03-04",
        )
        self.assertIn("X-Api-Key", m.last_request.headers)

    @requests_mock.Mocker()
    def test_create_zaakobject_bag_nlx(self, m):
        """
        Assuming the BAG has been configured to not require Auth header with NLX,
        connect a BAG Pand to a ZAAK fetching the object through an NLX outway.
        """
        mock_pand_get(
            m,
            "http://outway.nlx:8443/kadaster/bag/panden/0344100000011708?geldigOp=2020-03-04",
            "https://bag.basisregistraties.overheid.nl/api/v1/panden/0344100000011708?geldigOp=2020-03-04",
        )
        Service.objects.create(
            api_root="https://bag.basisregistraties.overheid.nl/api/v1/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            label="BAG",
            nlx="http://outway.nlx:8443/kadaster/bag/",
        )

        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "objectType": ZaakobjectTypes.pand,
            "relatieomschrijving": "",
            "object": "https://bag.basisregistraties.overheid.nl/api/v1/panden/0344100000011708?geldigOp=2020-03-04",
        }

        resp = self.client.post(url, data)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(
            m.last_request.url,
            "http://outway.nlx:8443/kadaster/bag/panden/0344100000011708?geldigOp=2020-03-04",
        )
        self.assertNotIn("X-Api-Key", m.last_request.headers)
