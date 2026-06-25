# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import unittest

from django.test import tag

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin
from openzaak.tests.utils.urls import reverse

from .factories import EnkelvoudigInformatieObjectFactory


@temp_private_root()
class EIOZoekTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy("documenten:enkelvoudiginformatieobject--zoek")

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

    @tag("gh-2406")
    @unittest.expectedFailure
    def test_zoek_with_experimental_params(self):
        # The experimental body attributes probably only work in the list filter
        # as query_params. Therefore I removed them from the OAS.
        eio1, eio2, _ = EnkelvoudigInformatieObjectFactory.create_batch(3)

        assert eio2.titel
        response = self.client.post(
            self.url,
            data={"uuid__in": [eio1.uuid, eio2.uuid], "titel": eio2.titel},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(eio2)}")

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
