# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.catalogi.tests.utils import (
    get_operation_url as get_catalogus_operation_url,
)
from openzaak.utils.tests import JWTAuthMixin

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@tag("external-urls")
class ListFilterLocalFKTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_besluittype(self):
        url = get_operation_url("besluit_list")
        type1, type2 = BesluitTypeFactory.create_batch(2)
        BesluitFactory.create_batch(3, besluittype=type1)
        BesluitFactory.create_batch(1, besluittype=type2)
        type1_url = get_catalogus_operation_url("besluittype_read", uuid=type1.uuid)

        response = self.client.get(
            url,
            {"besluittype": f"http://openzaak.nl{type1_url}"},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 3)


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
