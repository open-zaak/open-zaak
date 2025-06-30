# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.test import override_settings
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_validation_errors, reverse

from ..constants import Doelgroep
from ..models import SubStatus
from .factories import StatusFactory, SubStatusFactory, ZaakFactory


class SubStatusTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_detail_substatus(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        status_instance = StatusFactory.create(
            datum_status_gezet=timezone.now(), zaak=zaak
        )
        status_url = reverse(status_instance)
        substatus = SubStatusFactory.create(zaak=zaak, status=status_instance)
        detail_url = reverse(substatus)

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["status"], f"http://testserver{status_url}")

        expected_str = (
            f"SubStatus op {substatus.tijdstip} - {substatus.omschrijving[:20]}..."
        )
        self.assertEqual(str(substatus), expected_str)

    def test_list_substatus(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        status_instance = StatusFactory.create(
            datum_status_gezet=timezone.now(), zaak=zaak
        )
        status_url = reverse(status_instance)
        substatus1 = SubStatusFactory.create(
            zaak=zaak, status=status_instance, tijdstip="2022-01-01T12:00:00Z"
        )
        substatus2 = SubStatusFactory.create(
            zaak=zaak, status=status_instance, tijdstip="2022-01-05T12:00:00Z"
        )
        list_url = reverse(SubStatus)

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(
            data["results"][0]["url"], f"http://testserver{reverse(substatus2)}"
        )
        self.assertEqual(data["results"][0]["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["results"][0]["status"], f"http://testserver{status_url}")
        self.assertEqual(
            data["results"][1]["url"], f"http://testserver{reverse(substatus1)}"
        )
        self.assertEqual(data["results"][1]["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["results"][1]["status"], f"http://testserver{status_url}")

    def test_create_substatus(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        status_instance = StatusFactory.create(
            datum_status_gezet=timezone.now(), zaak=zaak
        )
        status_url = reverse(status_instance)
        list_url = reverse(SubStatus)

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "status": status_url,
                "omschrijving": "foo",
                "tijdstip": "2022-02-02T12:00:00Z",
                "doelgroep": Doelgroep.betrokkenen,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()

        self.assertEqual(data["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["status"], f"http://testserver{status_url}")
        self.assertEqual(data["tijdstip"], "2022-02-02T12:00:00Z")

    def test_create_substatus_without_status_use_current_status(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak)
        status2 = StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak)
        status_url = reverse(status2)
        list_url = reverse(SubStatus)

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "omschrijving": "foo",
                "tijdstip": "2022-02-02T12:00:00Z",
                "doelgroep": "betrokkenen",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()

        self.assertEqual(data["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["status"], f"http://testserver{status_url}")

    def test_create_substatus_without_status_and_no_statuses_on_zaak(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        list_url = reverse(SubStatus)

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "omschrijving": "foo",
                "tijdstip": "2022-02-02T12:00:00Z",
                "doelgroep": "betrokkenen",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn("invalidParams", data)

        invalid_status = next(
            (param for param in data["invalidParams"] if param["name"] == "status"),
            None,
        )
        self.assertIsNotNone(invalid_status)
        self.assertEqual(
            invalid_status["reason"],
            "No status was provided and the case has no associated status. A substatus can only be created if there is at least one status.",
        )

    def test_create_substatus_use_default_tijdstip(self):
        zaak = ZaakFactory.create()
        status_obj = StatusFactory.create(zaak=zaak)
        zaak_url = reverse(zaak)
        status_url = reverse(status_obj)
        list_url = reverse(SubStatus)

        with freeze_time("2020-01-01T12:00:00"):
            response = self.client.post(
                list_url,
                {
                    "zaak": zaak_url,
                    "status": status_url,
                    "omschrijving": "foo",
                    "doelgroep": "betrokkenen",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()

        self.assertEqual(data["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["tijdstip"], "2020-01-01T12:00:00Z")

    def test_create_substatus_use_default_doelgroep(self):
        zaak = ZaakFactory.create()
        status_obj = StatusFactory.create(zaak=zaak)  # renamed from `status`
        zaak_url = reverse(zaak)
        status_url = reverse(status_obj)
        list_url = reverse(SubStatus)

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "status": status_url,
                "omschrijving": "foo",
                "tijdstip": "2022-02-02T12:00:00Z",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["zaak"], f"http://testserver{zaak_url}")
        self.assertEqual(data["doelgroep"], "betrokkenen")


class SubStatusValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_substatus_validate_status_belongs_to_zaak(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        status_instance = StatusFactory.create(datum_status_gezet=timezone.now())
        status_url = reverse(status_instance)
        list_url = reverse(SubStatus)

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "status": status_url,
                "omschrijving": "foo",
                "tijdstip": "2022-02-02T12:00:00Z",
                "doelgroep": "betrokkenen",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")

        self.assertEqual(error["code"], "zaak-status-mismatch")


@override_settings(ALLOWED_HOSTS=["testserver", "testserver.com"])
class SubStatusFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list_substatus_filter_by_zaak(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        status_instance = StatusFactory.create(
            datum_status_gezet=timezone.now(), zaak=zaak
        )
        status_url = reverse(status_instance)
        substatus1 = SubStatusFactory.create(
            zaak=zaak,
            status=status_instance,
            tijdstip="2022-01-01T12:00:00Z",
        )
        substatus2 = SubStatusFactory.create(
            zaak=zaak,
            status=status_instance,
            tijdstip="2022-01-05T12:00:00Z",
        )

        zaak2 = ZaakFactory.create()
        status2 = StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak2)
        SubStatusFactory.create(zaak=zaak2, status=status2)
        SubStatusFactory.create(zaak=zaak2, status=status2)

        list_url = reverse(SubStatus)

        response = self.client.get(
            list_url,
            {"zaak": f"http://testserver.com{zaak_url}"},
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(
            data["results"][0]["url"], f"http://testserver.com{reverse(substatus2)}"
        )
        self.assertEqual(data["results"][0]["zaak"], f"http://testserver.com{zaak_url}")
        self.assertEqual(
            data["results"][0]["status"], f"http://testserver.com{status_url}"
        )
        self.assertEqual(
            data["results"][1]["url"], f"http://testserver.com{reverse(substatus1)}"
        )
        self.assertEqual(data["results"][1]["zaak"], f"http://testserver.com{zaak_url}")
        self.assertEqual(
            data["results"][1]["status"], f"http://testserver.com{status_url}"
        )

    def test_list_substatus_filter_by_doelgroep(self):
        zaak = ZaakFactory.create()
        status_instance = StatusFactory.create(
            datum_status_gezet=timezone.now(), zaak=zaak
        )
        status_url1 = reverse(status_instance)
        substatus1 = SubStatusFactory.create(
            zaak=zaak,
            status=status_instance,
            doelgroep=Doelgroep.betrokkenen,
            tijdstip="2022-01-01T12:00:00Z",
        )
        SubStatusFactory.create(
            zaak=zaak, status=status_instance, doelgroep=Doelgroep.intern
        )

        zaak2 = ZaakFactory.create()
        status2 = StatusFactory.create(datum_status_gezet=timezone.now(), zaak=zaak2)
        status_url2 = reverse(status2)
        substatus2 = SubStatusFactory.create(
            zaak=zaak2,
            status=status2,
            doelgroep=Doelgroep.betrokkenen,
            tijdstip="2022-01-05T12:00:00Z",
        )
        SubStatusFactory.create(zaak=zaak2, status=status2, doelgroep=Doelgroep.intern)

        list_url = reverse(SubStatus)

        response = self.client.get(
            list_url,
            {"doelgroep": Doelgroep.betrokkenen},
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(
            data["results"][0]["url"], f"http://testserver.com{reverse(substatus2)}"
        )
        self.assertEqual(
            data["results"][0]["status"], f"http://testserver.com{status_url2}"
        )
        self.assertEqual(
            data["results"][1]["url"], f"http://testserver.com{reverse(substatus1)}"
        )
        self.assertEqual(
            data["results"][1]["status"], f"http://testserver.com{status_url1}"
        )

    def test_list_substatus_filter_by_tijdstip(self):
        zaak = ZaakFactory.create()
        status_instance = StatusFactory.create(zaak=zaak)
        substatus_early = SubStatusFactory.create(
            zaak=zaak, status=status_instance, tijdstip="2022-01-01T12:00:00Z"
        )
        substatus_mid = SubStatusFactory.create(
            zaak=zaak, status=status_instance, tijdstip="2022-01-05T12:00:00Z"
        )
        substatus_late = SubStatusFactory.create(
            zaak=zaak, status=status_instance, tijdstip="2022-01-10T12:00:00Z"
        )

        url = reverse(SubStatus)

        test_cases = [
            ({"tijdstip__gt": "2022-01-05T12:00:00Z"}, [substatus_late]),
            ({"tijdstip__lt": "2022-01-05T12:00:00Z"}, [substatus_early]),
            (
                {"tijdstip__gte": "2022-01-05T12:00:00Z"},
                [substatus_mid, substatus_late],
            ),
            (
                {"tijdstip__lte": "2022-01-05T12:00:00Z"},
                [substatus_early, substatus_mid],
            ),
        ]

        for params, expected_substatuses in test_cases:
            with self.subTest(params=params):
                response = self.client.get(url, params, HTTP_HOST="testserver.com")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()
                expected_urls = {
                    f"http://testserver.com{reverse(sub)}"
                    for sub in expected_substatuses
                }
                returned_urls = {result["url"] for result in data["results"]}

                self.assertEqual(expected_urls, returned_urls)

    def test_list_substatus_filter_by_status(self):
        zaak = ZaakFactory.create()
        status1 = StatusFactory.create(zaak=zaak)
        status2 = StatusFactory.create(zaak=zaak)

        sub1 = SubStatusFactory.create(zaak=zaak, status=status1)
        SubStatusFactory.create(zaak=zaak, status=status2)

        url = reverse(SubStatus)
        response = self.client.get(
            url,
            {"status": f"http://testserver.com{reverse(status1)}"},
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["results"][0]["url"], f"http://testserver.com{reverse(sub1)}"
        )
