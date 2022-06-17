# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.contrib.gis.geos import Point
from django.test import tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.catalogi.tests.factories.catalogus import CatalogusFactory
from openzaak.tests.utils.auth import JWTAuthMixin

from .constants import POLYGON_AMSTERDAM_CENTRUM
from .factories import (
    ResultaatFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
)
from .utils import (
    ZAAK_READ_KWARGS,
    ZAAK_WRITE_KWARGS,
    get_catalogus_response,
    get_operation_url,
    get_zaaktype_response,
)


@tag("inclusions")
class ZakenIncludeTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.catalogus = CatalogusFactory.create()
        cls.zaaktype = ZaakTypeFactory.create(concept=False, catalogus=cls.catalogus)
        cls.zaaktype_url = reverse(cls.zaaktype)
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_url = reverse(cls.statustype)
        cls.statustype2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype2_url = reverse(cls.statustype2)

        super().setUpTestData()

    def test_zaak_list_include(self):
        """
        Test if related resources that are in the local database can be included
        """
        hoofdzaak = ZaakFactory(zaaktype=self.zaaktype)
        zaak = ZaakFactory.create(zaaktype=self.zaaktype, hoofdzaak=hoofdzaak)
        zaak_status = StatusFactory(zaak=zaak)
        resultaat = ResultaatFactory(zaak=zaak)
        eigenschap = ZaakEigenschapFactory(zaak=zaak)

        url = reverse("zaak-list")

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        eigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()

        response = self.client.get(
            url,
            {"include": "hoofdzaak,zaaktype,status,resultaat,eigenschappen"},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        expected = {
            "zaken:zaak": [hoofdzaak_data],
            "catalogi:zaaktype": [zaaktype_data],
            "zaken:resultaat": [resultaat_data],
            "zaken:status": [status_data],
            "zaken:zaakeigenschap": [eigenschap_data],
        }

        self.assertEqual(data["results"], [zaak_data, hoofdzaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(data["inclusions"], expected)

    def test_zaak_zoek_include(self):
        """
        Test if related resources that are in the local database can be included
        """
        hoofdzaak = ZaakFactory(zaaktype=self.zaaktype)
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            hoofdzaak=hoofdzaak,
            zaakgeometrie=Point(4.887990, 52.377595),
        )
        zaak_status = StatusFactory(zaak=zaak)
        resultaat = ResultaatFactory(zaak=zaak)
        eigenschap = ZaakEigenschapFactory(zaak=zaak)

        url = get_operation_url("zaak__zoek")

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        eigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                },
                "include": [
                    "hoofdzaak",
                    "zaaktype",
                    "status",
                    "resultaat",
                    "eigenschappen",
                ],
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        expected = {
            "zaken:zaak": [hoofdzaak_data],
            "catalogi:zaaktype": [zaaktype_data],
            "zaken:resultaat": [resultaat_data],
            "zaken:status": [status_data],
            "zaken:zaakeigenschap": [eigenschap_data],
        }

        self.assertEqual(data["results"], [zaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(data["inclusions"], expected)

    def test_zaak_list_include_wildcard(self):
        """
        Test if all related resources that are in the local database can be included
        with a wildcard
        """
        # Explicitly set a UUID, because the ordering of inclusions seems a bit funky
        hoofdzaak = ZaakFactory(
            zaaktype=self.zaaktype, uuid="da0e1b14-bdc8-466b-b145-a0c49081a466"
        )
        hoofdzaak_status = StatusFactory(
            zaak=hoofdzaak, uuid="da0e1b14-bdc8-466b-b145-a0c49081a466"
        )
        hoofdzaak_resultaat = ResultaatFactory(
            zaak=hoofdzaak, uuid="da0e1b14-bdc8-466b-b145-a0c49081a466"
        )
        hoofdzaak_eigenschap = ZaakEigenschapFactory(zaak=hoofdzaak)

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            hoofdzaak=hoofdzaak,
            uuid="bedc3f70-bcb9-4ee7-b3c8-1782c3dd8707",
        )
        zaak_status = StatusFactory(
            zaak=zaak,
            statustype=hoofdzaak_status.statustype,
            uuid="bedc3f70-bcb9-4ee7-b3c8-1782c3dd8707",
        )
        resultaat = ResultaatFactory(
            zaak=zaak,
            resultaattype=hoofdzaak_resultaat.resultaattype,
            uuid="bedc3f70-bcb9-4ee7-b3c8-1782c3dd8707",
        )
        eigenschap = ZaakEigenschapFactory(
            zaak=zaak, eigenschap=hoofdzaak_eigenschap.eigenschap
        )

        url = reverse("zaak-list")

        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_status_data = self.client.get(reverse(hoofdzaak_status)).json()
        hoofdzaak_resultaat_data = self.client.get(reverse(hoofdzaak_resultaat)).json()
        hoofdzaak_zaakeigenschap_data = self.client.get(
            reverse(hoofdzaak_eigenschap, kwargs={"zaak_uuid": hoofdzaak.uuid})
        ).json()

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        zaakeigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()
        zaak_statustype_data = self.client.get(reverse(zaak_status.statustype)).json()
        zaak_resultaattype_data = self.client.get(
            reverse(resultaat.resultaattype)
        ).json()
        zaak_eigenschap_data = self.client.get(reverse(eigenschap.eigenschap)).json()

        response = self.client.get(url, {"include": "*"}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        expected = {
            "zaken:zaak": [zaak_data, hoofdzaak_data],
            "zaken:resultaat": [resultaat_data, hoofdzaak_resultaat_data],
            "zaken:status": [status_data, hoofdzaak_status_data],
            "zaken:zaakeigenschap": [
                zaakeigenschap_data,
                hoofdzaak_zaakeigenschap_data,
            ],
            "catalogi:zaaktype": [zaaktype_data],
            "catalogi:statustype": [zaak_statustype_data],
            "catalogi:resultaattype": [zaak_resultaattype_data],
            "catalogi:eigenschap": [zaak_eigenschap_data],
        }

        self.assertEqual(data["results"], [zaak_data, hoofdzaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(data["inclusions"], expected)

    def test_zaak_list_include_nested(self):
        """
        Test if nested related resources that are in the local database can be included
        """
        hoofdzaak = ZaakFactory.create(zaaktype=self.zaaktype)
        resultaat1 = ResultaatFactory.create(zaak=hoofdzaak)
        zaak = ZaakFactory.create(zaaktype=self.zaaktype, hoofdzaak=hoofdzaak)
        ResultaatFactory.create(zaak=zaak)

        url = reverse("zaak-list")

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        resultaat_data = self.client.get(reverse(resultaat1)).json()
        resultaattype_data = self.client.get(reverse(resultaat1.resultaattype)).json()

        response = self.client.get(
            url,
            {
                "include": "hoofdzaak,hoofdzaak.resultaat,hoofdzaak.resultaat.resultaattype"
            },
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        self.assertEqual(data["results"], [zaak_data, hoofdzaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(
            data["inclusions"],
            {
                "zaken:zaak": [hoofdzaak_data],
                "zaken:resultaat": [resultaat_data],
                "catalogi:resultaattype": [resultaattype_data],
            },
        )


@tag("external-urls", "inclusions")
class ZakenExternalIncludeTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_zaak_list_include(self):
        """
        Test if related resources that are external can be included
        """
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)
        catalogus_data = get_catalogus_response(catalogus, zaaktype)

        zaak = ZaakFactory.create(zaaktype=zaaktype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()

        url = reverse("zaak-list")

        with requests_mock.Mocker() as m:
            m.get(zaaktype, json=zaaktype_data)
            m.get(catalogus, json=catalogus_data)
            response = self.client.get(
                url, {"include": "zaaktype"}, **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        self.assertEqual(data["results"], [zaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(data["inclusions"], {"catalogi:zaaktype": [zaaktype_data]})

    def test_zaak_list_include_nested(self):
        """
        Test if nested related resources that are external can be included
        """
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"

        hoofdzaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak = ZaakFactory.create(zaaktype=zaaktype, hoofdzaak=hoofdzaak)

        url = reverse("zaak-list")

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        catalogus_data = get_catalogus_response(catalogus, zaaktype)
        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)

        with requests_mock.Mocker() as m:
            m.get(zaaktype, json=zaaktype_data)
            m.get(catalogus, json=catalogus_data)
            response = self.client.get(
                url, {"include": "hoofdzaak,hoofdzaak.zaaktype"}, **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # `response.data` does not generate the rendered response
        data = response.json()

        self.assertEqual(data["results"], [zaak_data, hoofdzaak_data])
        self.assertIn("inclusions", data)
        self.assertEqual(
            data["inclusions"],
            {"zaken:zaak": [hoofdzaak_data], "catalogi:zaaktype": [zaaktype_data],},
        )
