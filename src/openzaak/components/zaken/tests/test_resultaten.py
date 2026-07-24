# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from .factories import ResultaatFactory, ZaakFactory
from .utils import get_operation_url


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ResultaatCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("resultaat_create")

    def test_create_external_resultaattype_fail_bad_url(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)

        response = self.client.post(
            self.list_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "resultaattype": "abcd",
                "toelichting": "some desc",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "resultaattype")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_resultaattype_fail_not_json_url(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)

        ServiceFactory.create(
            api_root="http://example.com/",
            api_type=APITypes.ztc,
        )

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                self.list_url,
                {
                    "zaak": f"http://testserver{zaak_url}",
                    "resultaattype": "http://example.com/",
                    "toelichting": "some desc",
                },
            )

        error = get_validation_errors(response, "resultaattype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_resultaattype_fail_unknown_resource(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)

        response = self.client.post(
            self.list_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "resultaattype": "https://other-externe.catalogus.nl/api/v1/resultaattypen/1",
                "toelichting": "some desc",
            },
        )

        error = get_validation_errors(response, "resultaattype")
        self.assertEqual(error["code"], "unknown-service")

    def test_pagination_pagesize_param(self):
        ResultaatFactory.create_batch(10)

        response = self.client.get(self.list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )
