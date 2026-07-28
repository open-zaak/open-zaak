# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors

from openzaak.components.catalogi.models import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse


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

        url = f"{reverse('catalogi:informatieobjecttype-list')}?omschrijving__icontains=descript"
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
