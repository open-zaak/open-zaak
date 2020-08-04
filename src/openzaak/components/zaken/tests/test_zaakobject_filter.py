# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ZaakobjectTypes

from openzaak.utils.tests import JWTAuthMixin

from .factories import ZaakObjectFactory
from .utils import get_operation_url


class ZaakObjectFilterTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_filter_type(self):
        zaakobject1 = ZaakObjectFactory.create(object_type=ZaakobjectTypes.besluit)
        ZaakObjectFactory.create(object_type=ZaakobjectTypes.adres)
        zaakobject1_url = get_operation_url("zaakobject_read", uuid=zaakobject1.uuid)
        url = get_operation_url("zaakobject_list")

        response = self.client.get(url, {"objectType": ZaakobjectTypes.besluit})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaakobject1_url}")

    def test_filter_zaak(self):
        zaakobject1 = ZaakObjectFactory.create()
        ZaakObjectFactory.create()
        zaak = zaakobject1.zaak
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaakobject1_url = get_operation_url("zaakobject_read", uuid=zaakobject1.uuid)
        url = get_operation_url("zaakobject_list")

        response = self.client.get(
            url, {"zaak": f"http://openzaak.nl{zaak_url}"}, HTTP_HOST="openzaak.nl"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://openzaak.nl{zaakobject1_url}")

    def test_filter_object(self):
        zaakobject1 = ZaakObjectFactory.create(object="http://example.com/objects/1")
        ZaakObjectFactory.create(object="http://example.com/objects/2")
        zaakobject1_url = get_operation_url("zaakobject_read", uuid=zaakobject1.uuid)
        url = get_operation_url("zaakobject_list")

        response = self.client.get(url, {"object": "http://example.com/objects/1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaakobject1_url}")
