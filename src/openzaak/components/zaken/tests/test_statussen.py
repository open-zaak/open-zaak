# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime

from django.test import override_settings, tag
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import StatusTypeFactory
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import Status
from .factories import ResultaatFactory, RolFactory, StatusFactory, ZaakFactory
from .utils import (
    ZAAK_READ_KWARGS,
    get_operation_url,
    get_resultaattype_response,
    get_statustype_response,
    get_zaaktype_response,
)


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
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
            list_url,
            {"zaak": f"http://openzaak.nl{zaak_url}"},
            headers={"host": "openzaak.nl"},
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

    def test_current_status_correctly_ordered(self):
        """
        Assert that the most recent status is reported as current status.

        Regression test for #1213.
        """
        zaak = ZaakFactory.create()
        # lower PK, but more recent date
        status1 = StatusFactory.create(
            zaak=zaak,
            datum_status_gezet=timezone.make_aware(datetime(2022, 7, 18, 10, 0, 0)),
        )
        # higher pk, but older date
        StatusFactory.create(
            zaak=zaak,
            datum_status_gezet=timezone.make_aware(datetime(2022, 7, 18, 8, 0, 0)),
        )
        detail_endpoint = reverse(zaak)

        response = self.client.get(detail_endpoint, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["status"], f"http://testserver{reverse(status1)}"
        )

    def test_create_status_with_rol(self):
        url = reverse("status-list")
        zaak = ZaakFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        rol = RolFactory.create(zaak=zaak, roltype__zaaktype=zaak.zaaktype)

        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "statustype": f"http://testserver{reverse(statustype)}",
            "datumStatusGezet": "2023-01-01T00:00:00",
            "gezetdoor": f"http://testserver{reverse(rol)}",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        status_ = Status.objects.get()
        self.assertEqual(status_.gezetdoor, rol)

    def test_create_status_with_rol_from_other_zaak(self):
        url = reverse("status-list")
        zaak = ZaakFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        rol = RolFactory.create()

        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "statustype": f"http://testserver{reverse(statustype)}",
            "datumStatusGezet": "2023-01-01T00:00:00",
            "gezetdoor": f"http://testserver{reverse(rol)}",
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaak-mismatch")

    def test_pagination_pagesize_param(self):
        StatusFactory.create_batch(10)
        url = reverse("status-list")

        response = self.client.get(url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(data["next"], f"http://testserver{url}?page=2&pageSize=5")


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

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(statustype, json=get_statustype_response(statustype, zaaktype))
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))

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

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
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
        ServiceFactory.create(api_root="http://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker() as m:
            m.get("http://example.com", status_code=200, text="<html></html>")

            response = self.client.post(
                self.list_url,
                {
                    "zaak": zaak_url,
                    "statustype": "http://example.com/",
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

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(
                statustype,
                json={
                    "url": statustype,
                    "zaaktype": zaaktype,
                    "isEindstatus": False,
                    "informeren": False,
                },
            )
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))

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

    def test_create_external_statustype_fail_unknown_service(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker() as m:
            m.get("http://example.com", status_code=200, text="<html></html>")

            response = self.client.post(
                self.list_url,
                {
                    "zaak": zaak_url,
                    "statustype": "https://other-externe.catalogus.nl/api/v1/statustypen/1",
                    "datumStatusGezet": "2018-10-18T20:00:00Z",
                },
            )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "unknown-service")


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class IsLastStatusTests(JWTAuthMixin, APITestCase):
    """
    test status.indicatieLaatstGezetteStatus
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.status11 = StatusFactory.create(datum_status_gezet=timezone.now())
        cls.status12 = StatusFactory.create(
            zaak=cls.status11.zaak, datum_status_gezet=timezone.now()
        )
        cls.status21 = StatusFactory.create(datum_status_gezet=timezone.now())
        cls.status22 = StatusFactory.create(
            zaak=cls.status21.zaak, datum_status_gezet=timezone.now()
        )

    def test_read_last_status(self):
        for first_status in [self.status11, self.status21]:
            with self.subTest(first_status):
                response = self.client.get(reverse(first_status))

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertFalse(response.json()["indicatieLaatstGezetteStatus"])

        for last_status in [self.status12, self.status22]:
            with self.subTest(first_status):
                response = self.client.get(reverse(last_status))

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.json()["indicatieLaatstGezetteStatus"])

    def test_filter_last_status(self):
        url = reverse_lazy("status-list")

        with self.subTest("indicatieLaatstGezetteStatus=True"):
            response = self.client.get(url, {"indicatieLaatstGezetteStatus": True})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)
            self.assertEqual(
                response.json()["results"][0]["uuid"], str(self.status22.uuid)
            )
            self.assertEqual(
                response.json()["results"][1]["uuid"], str(self.status12.uuid)
            )

        with self.subTest("indicatieLaatstGezetteStatus=False"):
            response = self.client.get(url, {"indicatieLaatstGezetteStatus": False})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)
            self.assertEqual(
                response.json()["results"][0]["uuid"], str(self.status21.uuid)
            )
            self.assertEqual(
                response.json()["results"][1]["uuid"], str(self.status11.uuid)
            )
