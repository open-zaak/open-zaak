# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.tests.utils import JWTAuthMixin

from ..models import Resultaat, Rol, Status, Zaak, ZaakInformatieObject, ZaakObject
from .factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_READ_KWARGS


class ResultaatFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "resultaattype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(reverse(Resultaat), {query_param: "bla"})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ResultaatFactory.create()
        for query_param in ["zaak", "resultaattype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(Resultaat), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class RolFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "roltype", "betrokkene"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(reverse(Rol), {query_param: "bla"})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        RolFactory.create()
        for query_param in ["zaak", "roltype", "betrokkene"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(Rol), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class StatusFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "statustype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(reverse(Status), {query_param: "bla"})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        StatusFactory.create()
        for query_param in ["zaak", "statustype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(Status), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class ZaakInformatieObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "bla"}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ZaakInformatieObjectFactory.create()
        for query_param in ["zaak", "informatieobject"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])


class ZaakObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaak", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(reverse(ZaakObject), {query_param: "bla"})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ZaakObjectFactory.create()
        for query_param in ["zaak", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class ZaakFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(
            reverse(Zaak), {"zaaktype": "bla"}, **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ZaakFactory.create()
        response = self.client.get(
            reverse(Zaak), {"zaaktype": "https://google.com"}, **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )

    @tag("gh-1023")
    def test_filter_by_rol_omschrijving_generiek_no_duplicate_results(self):
        """
        Assert that filtering on rol__omschrijvingGeneriek does not return duplicate results.

        Regression test for bug reported in #1023
        """
        zaak = ZaakFactory.create()
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )

        response = self.client.get(
            reverse(Zaak),
            {"rol__omschrijvingGeneriek": "behandelaar"},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_startdatum(self):
        ZaakFactory.create(startdatum="2019-01-01")
        ZaakFactory.create(startdatum="2019-03-01")
        url = reverse("zaak-list")

        response_gt = self.client.get(
            url, {"startdatum__gt": "2019-02-01"}, **ZAAK_READ_KWARGS
        )
        response_lt = self.client.get(
            url, {"startdatum__lt": "2019-02-01"}, **ZAAK_READ_KWARGS
        )
        response_gte = self.client.get(
            url, {"startdatum__gte": "2019-03-01"}, **ZAAK_READ_KWARGS
        )
        response_lte = self.client.get(
            url, {"startdatum__lte": "2019-01-01"}, **ZAAK_READ_KWARGS
        )

        for response in [response_gt, response_lt, response_gte, response_lte]:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

        self.assertEqual(response_gt.data["results"][0]["startdatum"], "2019-03-01")
        self.assertEqual(response_lt.data["results"][0]["startdatum"], "2019-01-01")
        self.assertEqual(response_gte.data["results"][0]["startdatum"], "2019-03-01")
        self.assertEqual(response_lte.data["results"][0]["startdatum"], "2019-01-01")

    def test_sort_startdatum(self):
        ZaakFactory.create(startdatum="2019-01-01")
        ZaakFactory.create(startdatum="2019-03-01")
        ZaakFactory.create(startdatum="2019-02-01")
        url = reverse("zaak-list")

        response = self.client.get(url, {"ordering": "-startdatum"}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["results"]

        self.assertEqual(data[0]["startdatum"], "2019-03-01")
        self.assertEqual(data[1]["startdatum"], "2019-02-01")
        self.assertEqual(data[2]["startdatum"], "2019-01-01")

    def test_filter_max_vertrouwelijkheidaanduiding(self):
        zaak1 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak2 = ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim
        )

        url = reverse(Zaak)

        response = self.client.get(
            url,
            {
                "maximaleVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zaakvertrouwelijk
            },
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(zaak1)}",
        )
        self.assertNotEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(zaak2)}",
        )

    def test_filter_rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn_max_length(
        self,
    ):
        ZaakFactory.create(startdatum="2019-01-01")
        ZaakFactory.create(startdatum="2019-03-01")
        url = reverse("zaak-list")

        response = self.client.get(
            url,
            {"rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "0" * 10},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(
            response, "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn"
        )
        self.assertEqual(error["code"], "max_length")

    def test_filter_rol__betrokkeneIdentificatie__medewerker__identificatie_max_length(
        self,
    ):
        ZaakFactory.create(startdatum="2019-01-01")
        ZaakFactory.create(startdatum="2019-03-01")
        url = reverse("zaak-list")

        response = self.client.get(
            url,
            {"rol__betrokkeneIdentificatie__medewerker__identificatie": "0" * 25},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(
            response, "rol__betrokkeneIdentificatie__medewerker__identificatie"
        )
        self.assertEqual(error["code"], "max_length")
