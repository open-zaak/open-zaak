# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin

from .factories import KlantContactFactory


class KlantContactFactoryTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_list_klantcontact(self):
        KlantContactFactory.create_batch(2)
        list_url = reverse("klantcontact-list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 2)

    def test_list_klantcontact_page(self):
        KlantContactFactory.create_batch(2)
        list_url = reverse("klantcontact-list")

        response = self.client.get(list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 2)

    def test_deprecated(self):
        url = reverse("klantcontact-list")

        response = self.client.get(url)

        self.assertIn("Warning", response)
        msg = (
            "Deze endpoint is verouderd en zal binnenkort uit dienst worden genomen. "
            "Maak gebruik van de vervangende contactmomenten API."
        )
        self.assertEqual(response["Warning"], f'299 "http://testserver{url}" "{msg}"')
