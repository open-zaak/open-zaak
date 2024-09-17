# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import uuid

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ..constants import AfzenderTypes, PostAdresTypes
from ..models import Verzending
from .factories import EnkelvoudigInformatieObjectFactory, VerzendingFactory


class VerzendingAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list(self):
        """
        test pagination and ordering here, individual attributes are checked in test_read_* methods below
        """
        url = reverse(Verzending)
        verzending1, verzending2, verzending3 = VerzendingFactory.create_batch(3)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(response_data["count"], 3)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver{reverse(verzending3)}",
        )
        self.assertEqual(
            response_data["results"][1]["url"],
            f"http://testserver{reverse(verzending2)}",
        )
        self.assertEqual(
            response_data["results"][2]["url"],
            f"http://testserver{reverse(verzending1)}",
        )

    def test_pagination_pagesize_param(self):
        VerzendingFactory.create_batch(10)
        url = reverse(Verzending)

        response = self.client.get(url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["next"], f"http://testserver{url}?page=2&pageSize=5")

    def test_read_with_inner_address(self):
        verzending = VerzendingFactory.create(has_inner_address=True)
        url = reverse(verzending)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "betrokkene": verzending.betrokkene,
                "informatieobject": f"http://testserver{reverse(verzending.get_informatieobject())}",
                "aardRelatie": verzending.aard_relatie,
                "toelichting": verzending.toelichting,
                "ontvangstdatum": verzending.ontvangstdatum,
                "verzenddatum": verzending.verzenddatum,
                "contactPersoon": verzending.contact_persoon,
                "contactpersoonnaam": verzending.contactpersoonnaam,
                "binnenlandsCorrespondentieadres": {
                    "huisletter": verzending.binnenlands_correspondentieadres_huisletter,
                    "huisnummer": verzending.binnenlands_correspondentieadres_huisnummer,
                    "huisnummerToevoeging": verzending.binnenlands_correspondentieadres_huisnummer_toevoeging,
                    "naamOpenbareRuimte": verzending.binnenlands_correspondentieadres_naam_openbare_ruimte,
                    "postcode": verzending.binnenlands_correspondentieadres_postcode,
                    "woonplaatsnaam": verzending.binnenlands_correspondentieadres_woonplaatsnaam,
                },
                "buitenlandsCorrespondentieadres": {
                    "adresBuitenland_1": "",
                    "adresBuitenland_2": "",
                    "adresBuitenland_3": "",
                    "landPostadres": "",
                },
                "correspondentiePostadres": {
                    "postBusOfAntwoordnummer": None,
                    "postadresPostcode": "",
                    "postadresType": "",
                    "woonplaatsnaam": "",
                },
                "faxnummer": verzending.faxnummer,
                "emailadres": verzending.emailadres,
                "mijnOverheid": verzending.mijn_overheid,
                "telefoonnummer": verzending.telefoonnummer,
            },
        )

    def test_read_with_outer_address(self):
        verzending = VerzendingFactory.create(has_outer_address=True)
        url = reverse(verzending)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "betrokkene": verzending.betrokkene,
                "informatieobject": f"http://testserver{reverse(verzending.get_informatieobject())}",
                "aardRelatie": verzending.aard_relatie,
                "toelichting": verzending.toelichting,
                "ontvangstdatum": verzending.ontvangstdatum,
                "verzenddatum": verzending.verzenddatum,
                "contactPersoon": verzending.contact_persoon,
                "contactpersoonnaam": verzending.contactpersoonnaam,
                "binnenlandsCorrespondentieadres": {
                    "huisletter": "",
                    "huisnummer": None,
                    "huisnummerToevoeging": "",
                    "naamOpenbareRuimte": "",
                    "postcode": "",
                    "woonplaatsnaam": "",
                },
                "buitenlandsCorrespondentieadres": {
                    "adresBuitenland_1": verzending.buitenlands_correspondentieadres_adres_buitenland_1,
                    "adresBuitenland_2": verzending.buitenlands_correspondentieadres_adres_buitenland_2,
                    "adresBuitenland_3": verzending.buitenlands_correspondentieadres_adres_buitenland_3,
                    "landPostadres": verzending.buitenlands_correspondentieadres_land_postadres,
                },
                "correspondentiePostadres": {
                    "postBusOfAntwoordnummer": None,
                    "postadresPostcode": "",
                    "postadresType": "",
                    "woonplaatsnaam": "",
                },
                "faxnummer": verzending.faxnummer,
                "emailadres": verzending.emailadres,
                "mijnOverheid": verzending.mijn_overheid,
                "telefoonnummer": verzending.telefoonnummer,
            },
        )

    def test_read_with_post_address(self):
        verzending = VerzendingFactory.create(has_post_address=True)
        url = reverse(verzending)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "betrokkene": verzending.betrokkene,
                "informatieobject": f"http://testserver{reverse(verzending.get_informatieobject())}",
                "aardRelatie": verzending.aard_relatie,
                "toelichting": verzending.toelichting,
                "ontvangstdatum": verzending.ontvangstdatum,
                "verzenddatum": verzending.verzenddatum,
                "contactPersoon": verzending.contact_persoon,
                "contactpersoonnaam": verzending.contactpersoonnaam,
                "binnenlandsCorrespondentieadres": {
                    "huisletter": "",
                    "huisnummer": None,
                    "huisnummerToevoeging": "",
                    "naamOpenbareRuimte": "",
                    "postcode": "",
                    "woonplaatsnaam": "",
                },
                "buitenlandsCorrespondentieadres": {
                    "adresBuitenland_1": "",
                    "adresBuitenland_2": "",
                    "adresBuitenland_3": "",
                    "landPostadres": "",
                },
                "correspondentiePostadres": {
                    "postBusOfAntwoordnummer": verzending.correspondentie_postadres_postbus_of_antwoord_nummer,
                    "postadresPostcode": verzending.correspondentie_postadres_postcode,
                    "postadresType": verzending.correspondentie_postadres_postadrestype,
                    "woonplaatsnaam": verzending.correspondentie_postadres_woonplaatsnaam,
                },
                "faxnummer": verzending.faxnummer,
                "emailadres": verzending.emailadres,
                "mijnOverheid": verzending.mijn_overheid,
                "telefoonnummer": verzending.telefoonnummer,
            },
        )

    def test_create_with_inner_address(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(Verzending)
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "inner shipment",
            "contactPersoon": "http://example.com/contactperson/1",
            "binnenlandsCorrespondentieadres": {
                "huisletter": "A",
                "huisnummer": 10,
                "huisnummerToevoeging": "1",
                "naamOpenbareRuimte": "Amsterdam ruimte",
                "postcode": "1010AA",
                "woonplaatsnaam": "Amsterdam",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Verzending.objects.count(), 1)

        verzending = Verzending.objects.get()

        self.assertEqual(verzending.betrokkene, "http://example.com/betrokkene/1")
        self.assertEqual(verzending.informatieobject, eio.canonical)
        self.assertEqual(verzending.aard_relatie, AfzenderTypes.afzender)
        self.assertEqual(verzending.toelichting, "inner shipment")
        self.assertEqual(
            verzending.contact_persoon, "http://example.com/contactperson/1"
        )
        self.assertEqual(verzending.binnenlands_correspondentieadres_huisletter, "A")
        self.assertEqual(verzending.binnenlands_correspondentieadres_huisnummer, 10)
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_huisnummer_toevoeging, "1"
        )
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_naam_openbare_ruimte,
            "Amsterdam ruimte",
        )
        self.assertEqual(verzending.binnenlands_correspondentieadres_postcode, "1010AA")
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_woonplaatsnaam, "Amsterdam"
        )

    def test_create_with_outer_address(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(Verzending)
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "outer shipment",
            "contactPersoon": "http://example.com/contactperson/1",
            "buitenlandsCorrespondentieadres": {
                "adresBuitenland1": "19 Flower street",
                "adresBuitenland2": "Fairytown",
                "adresBuitenland3": "Neverland",
                "landPostadres": "http://example.com/lands/1",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Verzending.objects.count(), 1)

        verzending = Verzending.objects.get()

        self.assertEqual(verzending.betrokkene, "http://example.com/betrokkene/1")
        self.assertEqual(verzending.informatieobject, eio.canonical)
        self.assertEqual(verzending.toelichting, "outer shipment")
        self.assertEqual(
            verzending.buitenlands_correspondentieadres_adres_buitenland_1,
            "19 Flower street",
        )
        self.assertEqual(
            verzending.buitenlands_correspondentieadres_adres_buitenland_2, "Fairytown"
        )
        self.assertEqual(
            verzending.buitenlands_correspondentieadres_adres_buitenland_3, "Neverland"
        )
        self.assertEqual(
            verzending.buitenlands_correspondentieadres_land_postadres,
            "http://example.com/lands/1",
        )

    def test_create_with_post_address(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(Verzending)
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "post shipment",
            "contactPersoon": "http://example.com/contactperson/1",
            "correspondentiePostadres": {
                "postBusOfAntwoordnummer": 1,
                "postadresPostcode": "1010AA",
                "postadresType": PostAdresTypes.antwoordnummer,
                "woonplaatsnaam": "Amsterdam",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Verzending.objects.count(), 1)

        verzending = Verzending.objects.get()

        self.assertEqual(verzending.betrokkene, "http://example.com/betrokkene/1")
        self.assertEqual(verzending.informatieobject, eio.canonical)
        self.assertEqual(verzending.toelichting, "post shipment")
        self.assertEqual(
            verzending.correspondentie_postadres_postbus_of_antwoord_nummer, 1
        )
        self.assertEqual(verzending.correspondentie_postadres_postcode, "1010AA")
        self.assertEqual(
            verzending.correspondentie_postadres_postadrestype,
            PostAdresTypes.antwoordnummer,
        )
        self.assertEqual(
            verzending.correspondentie_postadres_woonplaatsnaam, "Amsterdam"
        )

    def test_create_no_address_fail(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(Verzending)
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "post shipment",
            "contactPersoon": "http://example.com/contactperson/1",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-address")

    def test_create_more_than_one_address_fail(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(Verzending)
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "post shipment",
            "contactPersoon": "http://example.com/contactperson/1",
            "mijnOverheid": True,
            "correspondentiePostadres": {
                "postBusOfAntwoordnummer": 1,
                "postadresPostcode": "1010AA",
                "postadresType": PostAdresTypes.antwoordnummer,
                "woonplaatsnaam": "Amsterdam",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-address")

    def test_update(self):
        verzending = VerzendingFactory.create(has_inner_address=True, toelichting="old")
        url = reverse(verzending)
        eio = EnkelvoudigInformatieObjectFactory.create()
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "new",
            "contactPersoon": "http://example.com/contactperson/1",
            "binnenlandsCorrespondentieadres": {
                "huisletter": "A",
                "huisnummer": 10,
                "huisnummerToevoeging": "1",
                "naamOpenbareRuimte": "Amsterdam ruimte",
                "postcode": "1010AA",
                "woonplaatsnaam": "Amsterdam",
            },
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        verzending = Verzending.objects.get()

        self.assertEqual(verzending.betrokkene, "http://example.com/betrokkene/1")
        self.assertEqual(verzending.informatieobject, eio.canonical)
        self.assertEqual(verzending.aard_relatie, AfzenderTypes.afzender)
        self.assertEqual(verzending.toelichting, "new")
        self.assertEqual(
            verzending.contact_persoon, "http://example.com/contactperson/1"
        )
        self.assertEqual(verzending.binnenlands_correspondentieadres_huisletter, "A")
        self.assertEqual(verzending.binnenlands_correspondentieadres_huisnummer, 10)
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_huisnummer_toevoeging, "1"
        )
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_naam_openbare_ruimte,
            "Amsterdam ruimte",
        )
        self.assertEqual(verzending.binnenlands_correspondentieadres_postcode, "1010AA")
        self.assertEqual(
            verzending.binnenlands_correspondentieadres_woonplaatsnaam, "Amsterdam"
        )

    def test_update_no_address_fail(self):
        verzending = VerzendingFactory.create(has_inner_address=True, toelichting="old")
        url = reverse(verzending)
        eio = EnkelvoudigInformatieObjectFactory.create()
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "new",
            "contactPersoon": "http://example.com/contactperson/1",
        }

        response = self.client.put(url, data)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-address")

    def test_update_more_than_one_address_fail(self):
        verzending = VerzendingFactory.create(has_inner_address=True, toelichting="old")
        url = reverse(verzending)
        eio = EnkelvoudigInformatieObjectFactory.create()
        data = {
            "betrokkene": "http://example.com/betrokkene/1",
            "informatieobject": f"http://testserver{reverse(eio)}",
            "aardRelatie": AfzenderTypes.afzender,
            "toelichting": "new",
            "contactPersoon": "http://example.com/contactperson/1",
            "mijnOverheid": True,
            "binnenlandsCorrespondentieadres": {
                "huisletter": "A",
                "huisnummer": 10,
                "huisnummerToevoeging": "1",
                "naamOpenbareRuimte": "Amsterdam ruimte",
                "postcode": "1010AA",
                "woonplaatsnaam": "Amsterdam",
            },
        }

        response = self.client.put(url, data)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-address")

    def test_partial_update(self):
        verzending = VerzendingFactory.create(has_inner_address=True, toelichting="old")
        url = reverse(verzending)

        response = self.client.patch(url, {"toelichting": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        verzending = Verzending.objects.get()

        self.assertEqual(verzending.toelichting, "new")

    def test_partial_update_same_address(self):
        verzending = VerzendingFactory.create(has_inner_address=True)
        url = reverse(verzending)

        response = self.client.patch(
            url,
            {
                "binnenlandsCorrespondentieadres": {
                    "huisletter": "A",
                    "huisnummer": 10,
                    "huisnummerToevoeging": "1",
                    "naamOpenbareRuimte": "new ruimte",
                    "postcode": "1010AA",
                    "woonplaatsnaam": "Amsterdam",
                },
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        verzending = Verzending.objects.get()

        self.assertEqual(
            verzending.binnenlands_correspondentieadres_naam_openbare_ruimte,
            "new ruimte",
        )

    def test_partial_update_other_address_fail(self):
        verzending = VerzendingFactory.create(has_inner_address=True)
        url = reverse(verzending)

        response = self.client.patch(
            url,
            {
                "correspondentiePostadres": {
                    "postBusOfAntwoordnummer": 1,
                    "postadresPostcode": "1010AA",
                    "postadresType": PostAdresTypes.antwoordnummer,
                    "woonplaatsnaam": "Amsterdam",
                },
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-address")

    def test_delete(self):
        verzending = VerzendingFactory.create(has_inner_address=True, toelichting="old")
        url = reverse(verzending)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Verzending.objects.exists())


class VerzendingFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy(Verzending)

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_list_filter_by_informatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver.com{reverse(eio)}"
        verzending = VerzendingFactory.create(informatieobject=eio.canonical)
        VerzendingFactory.create()

        response = self.client.get(
            self.url, {"informatieobject": eio_url}, headers={"host": "testserver.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver.com{reverse(verzending)}",
        )

    def test_list_filter_by_betrokkene(self):
        betrokkene = "http://example.com/betrokkene/1"
        verzending = VerzendingFactory.create(betrokkene=betrokkene)
        VerzendingFactory.create()

        response = self.client.get(self.url, {"betrokkene": betrokkene})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver{reverse(verzending)}",
        )

    def test_list_filter_by_aard_relatie(self):
        verzending = VerzendingFactory.create(aard_relatie=AfzenderTypes.afzender)
        VerzendingFactory.create(aard_relatie=AfzenderTypes.geadresseerde)

        response = self.client.get(self.url, {"aardRelatie": AfzenderTypes.afzender})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver{reverse(verzending)}",
        )

    def test_list_filter_by_unknown_parameter(self):
        response = self.client.get(self.url, {"foo": "bar"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_list_expand(self):
        verzending = VerzendingFactory.create()

        verzending_data = self.client.get(reverse(verzending)).json()
        io_data = self.client.get(reverse(verzending.get_informatieobject())).json()
        iotype_data = self.client.get(
            reverse(verzending.get_informatieobject().informatieobjecttype)
        ).json()

        response = self.client.get(
            self.url,
            {"expand": "informatieobject,informatieobject.informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [
            {
                **verzending_data,
                "_expand": {
                    "informatieobject": {
                        **io_data,
                        "_expand": {"informatieobjecttype": iotype_data},
                    }
                },
            }
        ]
        self.assertEqual(data, expected_results)

    def test_retrieve_expand(self):
        verzending = VerzendingFactory.create()
        url = reverse(verzending)

        verzending_data = self.client.get(url).json()
        io_data = self.client.get(reverse(verzending.get_informatieobject())).json()
        iotype_data = self.client.get(
            reverse(verzending.get_informatieobject().informatieobjecttype)
        ).json()

        response = self.client.get(
            url,
            {"expand": "informatieobject,informatieobject.informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_results = {
            **verzending_data,
            "_expand": {
                "informatieobject": {
                    **io_data,
                    "_expand": {"informatieobjecttype": iotype_data},
                }
            },
        }

        self.assertEqual(data, expected_results)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class VerzendingCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_verzending_cmis_not_supported(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        uuid_ = uuid.uuid4()
        endpoints = [
            ("GET", reverse("verzending-list")),
            ("PUT", reverse("verzending-detail", kwargs={"uuid": uuid_})),
            ("PATCH", reverse("verzending-detail", kwargs={"uuid": uuid_})),
            ("DELETE", reverse("verzending-detail", kwargs={"uuid": uuid_})),
        ]

        for method, url in endpoints:
            with self.subTest(f"{method} {url}"):
                response = self.client.generic(method, url)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["code"], "CMIS not supported")

        # separate test for create because we need input data for permission check
        url = reverse("verzending-list")
        with self.subTest(f"POST {url}"):
            response = self.client.post(
                url,
                data={
                    "informatieobject": f"http://testserver{reverse(informatieobject)}"
                },
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["code"], "CMIS not supported")

        # separate test for retrieve
        url = reverse("verzending-detail", kwargs={"uuid": uuid_})
        with self.subTest(f"GET {url}"):
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
