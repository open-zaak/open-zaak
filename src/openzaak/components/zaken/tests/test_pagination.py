# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.config.models import FeatureFlags
from openzaak.tests.utils import JWTAuthMixin

from ..models import Zaak
from .factories import ZaakFactory
from .utils import ZAAK_READ_KWARGS


class ZaakPaginationTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_pagination_default(self):
        ZaakFactory.create_batch(2)
        list_url = reverse(Zaak)

        response = self.client.get(list_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
        self.assertNotIn("countExact", response_data)

    def test_pagination_page_param(self):
        ZaakFactory.create_batch(2)
        list_url = reverse(Zaak)

        response = self.client.get(list_url, {"page": 1}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
        self.assertNotIn("countExact", response_data)


@patch(
    "openzaak.utils.pagination.FeatureFlags.get_solo",
    return_value=FeatureFlags(improved_pagination_performance=True),
)
class ZaakPaginationImprovedPerformanceFeatureFlagTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ZaakFactory.create_batch(11)

    @patch("openzaak.utils.pagination.PAGINATION_COUNT_LIMIT", 10)
    @patch("openzaak.utils.pagination.CustomPagination.page_size", 5)
    def test_pagination_page_param_improved_performance_count_not_exact(self, *m):
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

    @patch("openzaak.utils.pagination.PAGINATION_COUNT_LIMIT", 10)
    @patch("openzaak.utils.pagination.CustomPagination.page_size", 5)
    def test_pagination_page_param_improved_performance_last_page(self, *m):
        list_url = reverse(Zaak)

        response = self.client.get(list_url, {"page": 3}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        # Because this is the last page, the limit is higher number than the real count
        self.assertEqual(response_data["count"], 11)
        self.assertIsNotNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

        # Because the limit exceeds the real count, the count is exact
        self.assertTrue(response_data["countExact"])
