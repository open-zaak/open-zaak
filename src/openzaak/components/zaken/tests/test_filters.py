# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.utils.tests import JWTAuthMixin

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
