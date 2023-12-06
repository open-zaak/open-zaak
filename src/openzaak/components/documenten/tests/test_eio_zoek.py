# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from .factories import EnkelvoudigInformatieObjectFactory


class EIOZoekTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy("enkelvoudiginformatieobject--zoek")

    def test_zoek_uuid_in(self):
        eio1, eio2, eio3 = EnkelvoudigInformatieObjectFactory.create_batch(3)
        data = {"uuid__in": [eio1.uuid, eio2.uuid]}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        data = sorted(data, key=lambda eio: eio["identificatie"])

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(eio1)}")
        self.assertEqual(data[1]["url"], f"http://testserver{reverse(eio2)}")

    def test_zoek_without_params(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "empty_search_body")

    def test_zoek_with_filter_param(self):
        eio1, eio2, eio3 = EnkelvoudigInformatieObjectFactory.create_batch(3)
        data = {"uuid__in": [eio1.uuid, eio2.uuid], "identificatie": eio1.identificatie}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(eio1)}")

    def test_zoek_with_expand(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        EnkelvoudigInformatieObjectFactory.create()
        data = {"uuid__in": [eio.uuid], "expand": ["informatieobjecttype"]}

        eio_data = self.client.get(reverse(eio)).json()
        iotype_data = self.client.get(reverse(eio.informatieobjecttype)).json()

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [
            {**eio_data, "_expand": {"informatieobjecttype": iotype_data}}
        ]
        self.assertEqual(data, expected_results)
