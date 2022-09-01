# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als burger wil ik alle meldingen kunnen inzien in mijn omgeving, binnen mijn
gemeente zodat ik weet wat er speelt of dat een melding al gedaan is.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/42
"""
from datetime import date

from django.contrib.gis.geos import Point
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from .constants import POLYGON_AMSTERDAM_CENTRUM
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class US42TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_anoniem_binnen_ams_centrum_district(self):
        """
        Test dat zaken binnen een bepaald gebied kunnen opgevraagd worden.
        """
        # in district
        zaak = ZaakFactory.create(zaakgeometrie=Point(4.887990, 52.377595))  # LONG LAT
        # outside of district
        ZaakFactory.create(zaakgeometrie=Point(4.905650, 52.357621))
        # no geo set
        ZaakFactory.create()

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        detail_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        self.assertEqual(response_data[0]["url"], f"http://testserver{detail_url}")

    def test_filter_ook_zaaktype(self):
        zaaktype1 = ZaakTypeFactory.create()
        zaaktype2 = ZaakTypeFactory.create()
        zaaktype1_url = reverse(zaaktype1)

        # both in district
        ZaakFactory.create(zaakgeometrie=Point(4.887990, 52.377595), zaaktype=zaaktype1)
        ZaakFactory.create(zaakgeometrie=Point(4.887990, 52.377595), zaaktype=zaaktype2)

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                },
                "zaaktype": f"http://openzaak.nl{zaaktype1_url}",
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)


class ZaakZoekTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zoek_uuid_in(self):
        zaak1, zaak2, zaak3 = ZaakFactory.create_batch(3)
        url = get_operation_url("zaak__zoek")
        data = {"uuid__in": [zaak1.uuid, zaak2.uuid]}

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        data = sorted(data, key=lambda zaak: zaak["identificatie"])

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaak1)}")
        self.assertEqual(data[1]["url"], f"http://testserver{reverse(zaak2)}")

    def test_zoek_without_params(self):
        url = get_operation_url("zaak__zoek")

        response = self.client.post(url, {}, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "empty_search_body")

    @tag("gh-1198")
    def test_zoek_ordering(self):
        url = get_operation_url("zaak__zoek")
        zaak1 = ZaakFactory.create(startdatum=date(2022, 9, 1))
        zaak2 = ZaakFactory.create(startdatum=date(2021, 11, 14))
        body = {
            "uuid__in": [zaak1.uuid, zaak2.uuid],
            "ordering": "-startdatum",
        }

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()["results"]
        self.assertEqual(results[0]["identificatie"], zaak1.identificatie)
        self.assertEqual(results[1]["identificatie"], zaak2.identificatie)

    @tag("gh-1198")
    def test_zoek_filter_backend_fields(self):
        url = get_operation_url("zaak__zoek")
        ZaakFactory.create(startdatum=date(2022, 9, 1))
        zaak2 = ZaakFactory.create(startdatum=date(2022, 9, 1))
        body = {"identificatie": zaak2.identificatie}

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["identificatie"], zaak2.identificatie)
