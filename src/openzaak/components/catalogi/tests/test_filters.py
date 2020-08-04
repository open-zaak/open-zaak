# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.utils.tests import JWTAuthMixin

from ..models import (
    BesluitType,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from .factories import (
    BesluitTypeFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


class BesluitTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["catalogus", "zaaktypen", "informatieobjecttypen"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(reverse(BesluitType), {query_param: "bla"})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype.zaaktypen.clear()
        besluittype.informatieobjecttypen.clear()
        for query_param in ["catalogus", "zaaktypen", "informatieobjecttypen"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(BesluitType), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class EigenschapFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(Eigenschap), {"zaaktype": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        EigenschapFactory.create(zaaktype__concept=False)
        response = self.client.get(
            reverse(Eigenschap), {"zaaktype": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class InformatieObjectTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(InformatieObjectType), {"catalogus": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "catalogus")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype.zaaktypen.clear()

        response = self.client.get(
            reverse(InformatieObjectType), {"catalogus": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class ResultaatTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(ResultaatType), {"zaaktype": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ResultaatTypeFactory.create(zaaktype__concept=False)
        response = self.client.get(
            reverse(ResultaatType), {"zaaktype": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class RolTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(RolType), {"zaaktype": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        RolTypeFactory.create(zaaktype__concept=False)
        response = self.client.get(reverse(RolType), {"zaaktype": "https://google.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class StatusTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(StatusType), {"zaaktype": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        StatusTypeFactory.create(zaaktype__concept=False)
        response = self.client.get(
            reverse(StatusType), {"zaaktype": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class ZaakTypeInformatieObjectTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["zaaktype", "informatieobjecttype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakTypeInformatieObjectType), {query_param: "bla"}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        for query_param in ["zaaktype", "informatieobjecttype"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ZaakTypeInformatieObjectType),
                    {query_param: "https://google.com"},
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.data,
                    {"count": 0, "next": None, "previous": None, "results": []},
                )


class ZaakTypeFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(ZaakType), {"catalogus": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "catalogus")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype.informatieobjecttypen.clear()

        response = self.client.get(
            reverse(ZaakType), {"catalogus": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )
