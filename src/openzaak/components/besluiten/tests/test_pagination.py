# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import Besluit
from .factories import BesluitFactory


class BesluitPaginationTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    NAMESPACE = "besluiten"

    def test_pagination_default(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        BesluitFactory.create_batch(2)
        besluit_list_url = reverse(Besluit, namespace=self.NAMESPACE)

        response = self.client.get(besluit_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        BesluitFactory.create_batch(2)
        besluit_list_url = reverse(Besluit, namespace=self.NAMESPACE)

        response = self.client.get(besluit_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        BesluitFactory.create_batch(10)
        besluit_list_url = reverse(Besluit, namespace=self.NAMESPACE)

        response = self.client.get(besluit_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{besluit_list_url}?page=2&pageSize=5"
        )
