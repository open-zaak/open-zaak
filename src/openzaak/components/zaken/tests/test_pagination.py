# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.pagination import FuzzyPagination

from ..models import Zaak
from .factories import ZaakFactory
from .utils import ZAAK_READ_KWARGS


class ZaakPaginationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy("zaak-list")

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


# can't use override_settings here because it overrides after class init
@patch(
    "openzaak.components.zaken.api.viewsets.ZaakViewSet.pagination_class",
    FuzzyPagination,
)
@override_settings(FUZZY_PAGINATION=True)
class ZaakFuzzyPaginationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy("zaak-list")

    @override_settings(FUZZY_PAGINATION_COUNT_LIMIT=10)
    @patch("openzaak.utils.pagination.FuzzyPagination.page_size", 5)
    def test_pagination_page_param_count_not_exact(self, *m):
        ZaakFactory.create_batch(11)

        list_url = reverse(Zaak)

        response = self.client.get(list_url, {"page": 1}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        # Real count exceeds the limit
        self.assertEqual(response_data["count"], 10)
        self.assertIsNone(response_data["previous"])
        self.assertIsNotNone(response_data["next"])

        # Because the real count exceeds the limit, the count is not exact
        self.assertFalse(response_data["countExact"])

    @override_settings(FUZZY_PAGINATION_COUNT_LIMIT=10)
    @patch("openzaak.utils.pagination.FuzzyPagination.page_size", 5)
    def test_pagination_page_param_last_page_count_exact(self, *m):
        ZaakFactory.create_batch(11)

        response = self.client.get(self.list_url, {"page": 3}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        # Because this is the last page, the limit is higher number than the real count
        self.assertEqual(response_data["count"], 11)
        self.assertIsNotNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

        # Because the limit exceeds the real count, the count is exact
        self.assertTrue(response_data["countExact"])

    def test_pagination_no_page_param_count_exact(self, *m):
        ZaakFactory.create_batch(11)

        response = self.client.get(self.list_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(response_data["count"], 11)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
        self.assertTrue(response_data["countExact"])

    def test_pagination_pagesize_param(self):
        ZaakFactory.create_batch(11)

        response = self.client.get(self.list_url, {"pageSize": 5}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 11)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )
        self.assertTrue(data["countExact"])
