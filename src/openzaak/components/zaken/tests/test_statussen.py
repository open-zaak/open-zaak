# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import StatusTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from .factories import ResultaatFactory, StatusFactory, ZaakFactory
from .utils import (
    get_operation_url,
    get_resultaattype_response,
    get_statustype_response,
    get_zaaktype_response,
)


class StatusTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_filter_statussen_op_zaak(self):
        status1, status2 = StatusFactory.create_batch(2)
        assert status1.zaak != status2.zaak
        status1_url = reverse("status-detail", kwargs={"uuid": status1.uuid})
        status2_url = reverse("status-detail", kwargs={"uuid": status2.uuid})

        list_url = reverse("status-list")
        zaak_url = reverse("zaak-detail", kwargs={"uuid": status1.zaak.uuid})

        response = self.client.get(
            list_url, {"zaak": f"http://openzaak.nl{zaak_url}"}, HTTP_HOST="openzaak.nl"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://openzaak.nl{status1_url}")
        self.assertNotEqual(data[0]["url"], f"http://openzaak.nl{status2_url}")

    def test_create_malformed_uuid(self):
        """
        Assert that providing a malformed ZAAK URL raises validation errors.

        Regression test for https://github.com/open-zaak/open-zaak/issues/604
        """
        zaak = ZaakFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        zaak_url = f"http://testserver{reverse(zaak)}"
        data = {
            "zaak": f"{zaak_url} ",  # trailing space is deliberate!
            "statustype": f"http://testserver{reverse(statustype)}",
            "datumStatusGezet": "2020-05-28",
        }

        response = self.client.post(reverse("status-list"), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "zaak")
        self.assertIsNotNone(error)
        self.assertEqual(error["code"], "invalid")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class StatusCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("status_create")

    def test_create_external_statustype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        statustype = "https://externe.catalogus.nl/api/v1/statustypen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                "GET", statustype, json=get_statustype_response(statustype, zaaktype),
            )
            m.register_uri(
                "GET", zaaktype, json=get_zaaktype_response(catalogus, zaaktype),
            )

            response = self.client.post(
                self.list_url,
                {
                    "zaak": zaak_url,
                    "statustype": statustype,
                    "datumStatusGezet": "2018-10-18T20:00:00Z",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_statustype_last(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        statustype = "https://externe.catalogus.nl/api/v1/statustypen/7a3e4a22-d789-4381-939b-401dbce29426"
        resultaattype = "https://externe.catalogus.nl/api/v1/resultaattypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        statustype_data = get_statustype_response(statustype, zaaktype)
        statustype_data["isEindstatus"] = True

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver{reverse(zaak)}"
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)

        with requests_mock.Mocker(real_http=True) as m:
            m.get(statustype, json=statustype_data)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(
                resultaattype, json=get_resultaattype_response(resultaattype, zaaktype)
            )

            response = self.client.post(
                self.list_url,
                {
                    "zaak": zaak_url,
                    "statustype": statustype,
                    "datumStatusGezet": "2018-10-18T20:00:00Z",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_statustype_fail_bad_url(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        response = self.client.post(
            self.list_url,
            {
                "zaak": zaak_url,
                "statustype": "abcd",
                "datumStatusGezet": "2018-10-18T20:00:00Z",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_statustype_fail_not_json_url(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        response = self.client.post(
            self.list_url,
            {
                "zaak": zaak_url,
                "statustype": "http://example.com",
                "datumStatusGezet": "2018-10-18T20:00:00Z",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_statustype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        statustype = "https://externe.catalogus.nl/api/v1/statustypen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                "GET",
                statustype,
                json={
                    "url": statustype,
                    "zaaktype": zaaktype,
                    "isEindstatus": False,
                    "informeren": False,
                },
            )
            m.register_uri(
                "GET", zaaktype, json=get_zaaktype_response(catalogus, zaaktype),
            )

            response = self.client.post(
                self.list_url,
                {
                    "zaak": zaak_url,
                    "statustype": statustype,
                    "datumStatusGezet": "2018-10-18T20:00:00Z",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "invalid-resource")
