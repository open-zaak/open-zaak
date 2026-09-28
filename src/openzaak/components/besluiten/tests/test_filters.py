# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.catalogi.tests.utils import (
    get_operation_url as get_catalogus_operation_url,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ListFilterLocalFKTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = get_operation_url("besluit_list")

    def test_filter_besluittype(self):
        type1, type2 = BesluitTypeFactory.create_batch(2)
        BesluitFactory.create_batch(3, besluittype=type1)
        BesluitFactory.create_batch(1, besluittype=type2)
        type1_url = get_catalogus_operation_url("besluittype_read", uuid=type1.uuid)

        response = self.client.get(
            self.url,
            {"besluittype": f"http://openzaak.nl{type1_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 3)

    def test_filter_besluittype_not_found(self):
        type1, type2 = BesluitTypeFactory.create_batch(2)
        BesluitFactory.create_batch(1, besluittype=type1)
        type2_url = get_catalogus_operation_url("besluittype_read", uuid=type2.uuid)

        with self.subTest("besluitype exists"):
            response = self.client.get(
                self.url,
                {"besluittype": f"http://openzaak.nl{type2_url}"},
                headers={"host": "openzaak.nl"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)

        with self.subTest("external besluitype does not exist"):
            response = self.client.get(
                self.url,
                {
                    "besluittype": f"http://openzaak.nl/catalogi/api/v1/besluittypen/{uuid.uuid4()}"
                },
                headers={"host": "testserver"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)

        with self.subTest("local besluitype does not exist"):
            response = self.client.get(
                self.url,
                {
                    "besluittype": f"http://openzaak.nl/catalogi/api/v1/besluittypen/{uuid.uuid4()}"
                },
                headers={"host": "openzaak.nl"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)

    def test_filter_zaak(self):
        zaak1, zaak2 = ZaakFactory.create_batch(2)
        BesluitFactory.create_batch(3, zaak=zaak1)
        BesluitFactory.create_batch(1, zaak=zaak2)
        zaak1_url = reverse(zaak1)

        response = self.client.get(
            self.url,
            {"zaak": f"http://openzaak.nl{zaak1_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 3)

    def test_filter_zaak_not_found(self):
        zaak1, zaak2 = ZaakFactory.create_batch(2)
        BesluitFactory.create(zaak=zaak1)
        zaak2_url = reverse(zaak2)

        with self.subTest("zaak exists"):
            response = self.client.get(
                self.url,
                {"zaak": f"http://openzaak.nl{zaak2_url}"},
                headers={"host": "openzaak.nl"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)
        with self.subTest("external zaak does not exist"):
            response = self.client.get(
                self.url,
                {"zaak": f"http://openzaak.nl/zaken/api/v1/zaken/{uuid.uuid4()}"},
                headers={"host": "testserver"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)
        with self.subTest("local zaak does not exist"):
            response = self.client.get(
                self.url,
                {"zaak": f"http://openzaak.nl/zaken/api/v1/zaken/{uuid.uuid4()}"},
                headers={"host": "openzaak.nl"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["count"], 0)


class BesluitAPIFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_validate_unknown_query_params(self):
        BesluitFactory.create_batch(2)
        url = reverse(Besluit)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(Besluit), {"besluittype": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        BesluitFactory.create(besluittype__concept=False)
        response = self.client.get(
            reverse(Besluit), {"besluittype": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"count": 0, "next": None, "previous": None, "results": []}
        )


class BesluitInformatieObjectAPIFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_validate_unknown_query_params(self):
        BesluitInformatieObjectFactory.create_batch(2)
        url = reverse(BesluitInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_filter_by_invalid_url(self):
        response = self.client.get(reverse(BesluitInformatieObject), {"besluit": "bla"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluit")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        BesluitInformatieObjectFactory.create()
        response = self.client.get(
            reverse(BesluitInformatieObject), {"besluit": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
