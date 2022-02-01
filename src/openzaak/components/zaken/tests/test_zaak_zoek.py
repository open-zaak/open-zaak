# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als burger wil ik alle meldingen kunnen inzien in mijn omgeving, binnen mijn
gemeente zodat ik weet wat er speelt of dat een melding al gedaan is.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/42
"""
from django.contrib.gis.geos import Point
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
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


@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakZoekPermissionTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)

        super().setUpTestData()

    def test_zaak_zoek(self):
        """
        Regression test for filtering the Zaak list based on authorizations
        """

        zaaktype2 = ZaakTypeFactory.create(concept=False)

        # in district
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            zaakgeometrie=Point(4.887990, 52.377595),
        )  # LONG LAT
        #
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            zaakgeometrie=Point(4.887990, 52.377595),
        )
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaakgeometrie=Point(4.887990, 52.377595),
        )

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
