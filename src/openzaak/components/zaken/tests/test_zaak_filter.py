# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS


class ZaakFilterTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True
    url = reverse_lazy("zaak-list")

    def test_filter_bronorganisatie_in(self):
        zaak = ZaakFactory.create(bronorganisatie="517439943")
        ZaakFactory.create(bronorganisatie="736160221")

        response = self.client.get(
            self.url,
            {"bronorganisatie__in": "517439943,159351741"},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"], f"http://testserver{reverse(zaak)}"
        )

    def test_filter_on_archiefactiedatum(self):
        zaak1 = ZaakFactory.create(archiefactiedatum=date(2023, 1, 10))
        zaak2 = ZaakFactory.create(archiefactiedatum=date(2023, 1, 20))
        zaak3 = ZaakFactory.create(archiefactiedatum=None)

        with self.subTest("archiefactiedatum__lt"):
            response = self.client.get(
                self.url, {"archiefactiedatum__lt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

        with self.subTest("archiefactiedatum__gt"):
            response = self.client.get(
                self.url, {"archiefactiedatum__gt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak2)}",
            )

        with self.subTest("archiefactiedatum__isnull"):
            response = self.client.get(
                self.url, {"archiefactiedatum__isnull": True}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak3)}",
            )

    def test_filter_on_registratiedatum(self):
        zaak1 = ZaakFactory.create(registratiedatum=date(2023, 1, 10))
        zaak2 = ZaakFactory.create(registratiedatum=date(2023, 1, 20))
        zaak3 = ZaakFactory.create(registratiedatum=date(2023, 1, 12))

        with self.subTest("registratiedatum__lt"):
            response = self.client.get(
                self.url, {"registratiedatum__lt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

        with self.subTest("registratiedatum__gt"):
            response = self.client.get(
                self.url, {"registratiedatum__gt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak2)}",
            )

        with self.subTest("registratiedatum"):
            response = self.client.get(
                self.url, {"registratiedatum": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak3)}",
            )

    def test_filter_on_einddatum(self):
        zaak1 = ZaakFactory.create(einddatum=date(2023, 1, 10))
        zaak2 = ZaakFactory.create(einddatum=date(2023, 1, 20))
        zaak3 = ZaakFactory.create(einddatum=date(2023, 1, 12))
        zaak4 = ZaakFactory.create(einddatum=None)

        with self.subTest("einddatum__lt"):
            response = self.client.get(
                self.url, {"einddatum__lt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

        with self.subTest("einddatum__gt"):
            response = self.client.get(
                self.url, {"einddatum__gt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak2)}",
            )

        with self.subTest("einddatum"):
            response = self.client.get(
                self.url, {"einddatum": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak3)}",
            )

        with self.subTest("einddatum__isnull"):
            response = self.client.get(
                self.url, {"einddatum__isnull": True}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak4)}",
            )

    def test_filter_on_einddatum_gepland(self):
        zaak1 = ZaakFactory.create(einddatum_gepland=date(2023, 1, 10))
        zaak2 = ZaakFactory.create(einddatum_gepland=date(2023, 1, 20))
        zaak3 = ZaakFactory.create(einddatum_gepland=date(2023, 1, 12))

        with self.subTest("einddatumGepland__lt"):
            response = self.client.get(
                self.url, {"einddatumGepland__lt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

        with self.subTest("einddatumGepland__gt"):
            response = self.client.get(
                self.url, {"einddatumGepland__gt": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak2)}",
            )

        with self.subTest("einddatumGepland"):
            response = self.client.get(
                self.url, {"einddatumGepland": "2023-01-12"}, **ZAAK_WRITE_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak3)}",
            )

    def test_filter_on_uiterlijke_einddatum_afdoening(self):
        zaak1 = ZaakFactory.create(uiterlijke_einddatum_afdoening=date(2023, 1, 10))
        zaak2 = ZaakFactory.create(uiterlijke_einddatum_afdoening=date(2023, 1, 20))
        zaak3 = ZaakFactory.create(uiterlijke_einddatum_afdoening=date(2023, 1, 12))

        with self.subTest("uiterlijkeEinddatumAfdoening__lt"):
            response = self.client.get(
                self.url,
                {"uiterlijkeEinddatumAfdoening__lt": "2023-01-12"},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

        with self.subTest("uiterlijkeEinddatumAfdoening__gt"):
            response = self.client.get(
                self.url,
                {"uiterlijkeEinddatumAfdoening__gt": "2023-01-12"},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak2)}",
            )

        with self.subTest("uiterlijkeEinddatumAfdoening"):
            response = self.client.get(
                self.url,
                {"uiterlijkeEinddatumAfdoening": "2023-01-12"},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak3)}",
            )

    def test_filter_identificatie_icontains(self):
        zaak = ZaakFactory.create(identificatie="ZAAK-2024-0000000057")
        ZaakFactory.create(identificatie="ZAAK-2025-0000000001")

        response = self.client.get(
            self.url,
            {"identificatie__icontains": "2024"},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"], f"http://testserver{reverse(zaak)}"
        )

    def test_filter_omschrijving(self):
        zaak = ZaakFactory.create(omschrijving="Old case")
        ZaakFactory.create(omschrijving="New case")

        response = self.client.get(
            self.url,
            {"omschrijving": "old"},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"], f"http://testserver{reverse(zaak)}"
        )

    def test_filter_zaaktype_omschrijving(self):
        zaak = ZaakFactory.create(zaaktype__zaaktype_omschrijving="Old case type")
        ZaakFactory.create(zaaktype__zaaktype_omschrijving="New case type")

        response = self.client.get(
            self.url,
            {"zaaktype__omschrijving": "old"},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"], f"http://testserver{reverse(zaak)}"
        )
