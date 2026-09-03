# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from .factories import ZaakFactory
from .utils import ZAAK_READ_KWARGS


class ZaakPaginationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy("zaken:zaak-list")

    def test_pagination_default(self):
        ZaakFactory.create_batch(2)

        response = self.client.get(self.list_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
        self.assertNotIn("countExact", response_data)

    def test_pagination_page_param(self):
        ZaakFactory.create_batch(2)

        response = self.client.get(self.list_url, {"page": 1}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
        self.assertNotIn("countExact", response_data)

    def test_pagination_pagesize_param(self):
        ZaakFactory.create_batch(10)

        response = self.client.get(self.list_url, {"pageSize": 5}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )
