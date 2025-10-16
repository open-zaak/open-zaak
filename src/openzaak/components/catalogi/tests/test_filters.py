# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.tests.utils import JWTAuthMixin

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

    def test_filter_with_invalid_status_query_param(self):
        EigenschapFactory.create(zaaktype__concept=False)

        url = f"{reverse(Eigenschap)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")


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

    def test_filter_with_invalid_status_query_param(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype.zaaktypen.clear()

        url = f"{reverse(InformatieObjectType)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")

    def test_filter_by_omschrijving_icontains(self):
        obj1 = InformatieObjectTypeFactory.create(
            omschrijving="First Description", concept=False
        )
        obj2 = InformatieObjectTypeFactory.create(
            omschrijving="Second description", concept=False
        )
        obj3 = InformatieObjectTypeFactory.create(
            omschrijving="Another thing", concept=False
        )

        url = f"{reverse('informatieobjecttype-list')}?omschrijving__icontains=descript"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_urls = [
            item["url"].replace("http://testserver", "")
            for item in response.data["results"]
        ]
        self.assertEqual(response.data["count"], 2)
        self.assertIn(obj1.get_absolute_api_url(), returned_urls)
        self.assertIn(obj2.get_absolute_api_url(), returned_urls)
        self.assertNotIn(obj3.get_absolute_api_url(), returned_urls)


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

    def test_filter_with_invalid_status_query_param(self):
        ResultaatTypeFactory.create(zaaktype__concept=False)

        url = f"{reverse(ResultaatType)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")


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

    def test_filter_with_invalid_status_query_param(self):
        RolTypeFactory.create(zaaktype__concept=False)

        url = f"{reverse(RolType)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")


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

    def test_filter_with_invalid_status_query_param(self):
        StatusTypeFactory.create(zaaktype__concept=False)

        url = f"{reverse(StatusType)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")


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

    def test_filter_with_invalid_status_query_param(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype.informatieobjecttypen.clear()

        url = f"{reverse(ZaakType)}?status=alle"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "status")
        self.assertEqual(error["code"], "invalid_choice")

    def test_filter_by_omschrijving_icontains(self):
        obj1 = ZaakTypeFactory.create(
            zaaktype_omschrijving="First Description", concept=False
        )
        obj2 = ZaakTypeFactory.create(
            zaaktype_omschrijving="Second description", concept=False
        )
        obj3 = ZaakTypeFactory.create(
            zaaktype_omschrijving="Another thing", concept=False
        )

        url = f"{reverse(ZaakType)}?omschrijving__icontains=descript"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_urls = [
            item["url"].replace("http://testserver", "")
            for item in response.data["results"]
        ]
        self.assertEqual(response.data["count"], 2)
        self.assertIn(obj1.get_absolute_api_url(), returned_urls)
        self.assertIn(obj2.get_absolute_api_url(), returned_urls)
        self.assertNotIn(obj3.get_absolute_api_url(), returned_urls)

    def test_filter_by_identificatie_icontains(self):
        obj1 = ZaakTypeFactory.create(identificatie="ABC123", concept=False)
        obj2 = ZaakTypeFactory.create(identificatie="abc456", concept=False)
        obj3 = ZaakTypeFactory.create(identificatie="XYZ789", concept=False)

        url = f"{reverse(ZaakType)}?identificatie__icontains=abc"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_urls = [
            item["url"].replace("http://testserver", "")
            for item in response.data["results"]
        ]
        self.assertEqual(response.data["count"], 2)
        self.assertIn(obj1.get_absolute_api_url(), returned_urls)
        self.assertIn(obj2.get_absolute_api_url(), returned_urls)
        self.assertNotIn(obj3.get_absolute_api_url(), returned_urls)
