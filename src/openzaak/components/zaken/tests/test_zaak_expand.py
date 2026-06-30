# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.contrib.gis.geos import Point
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse_lazy

from openzaak.components.catalogi.api.scopes import (
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.catalogi.tests.factories.catalogus import CatalogusFactory
from openzaak.tests.utils.auth import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_CREATE,
)
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
    get_resultaattype_response,
    get_zaaktype_response,
)


@tag("expand")
class ZakenIncludeTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    url = reverse_lazy("zaken:zaak-list")

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

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        eigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()

        response = self.client.get(
            self.url,
            {"expand": "hoofdzaak,zaaktype,status,resultaat,eigenschappen"},
            **ZAAK_READ_KWARGS,
        )

        data = response.json()["results"]
        expected_results = [
            {
                **zaak_data,
                "_expand": {
                    "zaaktype": zaaktype_data,
                    "hoofdzaak": {
                        **hoofdzaak_data,
                        "_expand": {"zaaktype": zaaktype_data},
                    },
                    "eigenschappen": [eigenschap_data],
                    "status": status_data,
                    "resultaat": resultaat_data,
                },
            },
            {**hoofdzaak_data, "_expand": {"zaaktype": zaaktype_data}},
        ]
        self.assertEqual(data, expected_results)

    def test_zaak_list_no_expand(self):
        """
        Verify that the _expand key is also present if the expand query parameter is unused
        """
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()

        response = self.client.get(
            self.url,
            **ZAAK_READ_KWARGS,
        )

        data = response.json()["results"]
        expected_results = [
            {
                **zaak_data,
                "_expand": {},
            }
        ]

        self.assertEqual(data, expected_results)

    def test_zaak_retrieve_no_expand(self):
        """
        Verify that the _expand key is also present if the expand query parameter is unused
        """
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()

        response = self.client.get(
            reverse(zaak),
            **ZAAK_READ_KWARGS,
        )

        data = response.json()
        expected_results = {
            **zaak_data,
            "_expand": {},
        }

        self.assertEqual(data, expected_results)

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

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        eigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()

        # The detail responses also include the _expand attribute, but the list response
        # only has a _expand attribute at the root level (no _expand nested inside _expand)
        del zaak_data["_expand"]
        del hoofdzaak_data["_expand"]

        response = self.client.post(
            reverse("zaken:zaak--zoek"),
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                },
                "expand": [
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

        data = response.json()["results"]
        expected_results = [
            {
                **zaak_data,
                "_expand": {
                    "zaaktype": zaaktype_data,
                    "hoofdzaak": hoofdzaak_data,
                    "eigenschappen": [eigenschap_data],
                    "status": status_data,
                    "resultaat": resultaat_data,
                },
            },
        ]
        self.assertEqual(data, expected_results)

    def test_zaak_zoek_include_permissions(self):
        # disable all autorisaties
        self.applicatie.heeft_alle_autorisaties = False
        self.applicatie.save()

        zaak1, zaak2 = ZaakFactory.create_batch(2)
        url = reverse("zaak--zoek")
        data = {
            "uuid__in": [zaak1.uuid, zaak2.uuid],
            "expand": ["zaaktype"],
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # add only SCOPE_ZAKEN_ALLES_LEZEN
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            zaaktype=self.zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # Read zaaktypen is NOT allowed without catalogi scope
        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.ztc,
            scopes=[SCOPE_CATALOGI_READ],
        )

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zaak_list_include_nested(self):
        """
        Test if nested related resources that are in the local database can be included
        """
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        resultaat = ResultaatFactory.create(
            zaak=zaak, resultaattype__zaaktype=self.zaaktype
        )

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        resultaattype_data = self.client.get(reverse(resultaat.resultaattype)).json()

        response = self.client.get(
            self.url,
            {"expand": "resultaat,resultaat.resultaattype"},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [
            {
                **zaak_data,
                "_expand": {
                    "resultaat": {
                        **resultaat_data,
                        "_expand": {"resultaattype": resultaattype_data},
                    }
                },
            },
        ]
        self.assertEqual(data, expected_results)

    def test_zaak_retrieve_include(self):
        """
        Test for detail view
        """
        hoofdzaak = ZaakFactory(zaaktype=self.zaaktype)
        zaak = ZaakFactory.create(zaaktype=self.zaaktype, hoofdzaak=hoofdzaak)
        zaak_status = StatusFactory(zaak=zaak)
        resultaat = ResultaatFactory(zaak=zaak)
        eigenschap = ZaakEigenschapFactory(zaak=zaak)

        zaak_url = reverse(zaak)

        zaak_data = self.client.get(zaak_url, **ZAAK_READ_KWARGS).json()
        hoofdzaak_data = self.client.get(reverse(hoofdzaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        status_data = self.client.get(reverse(zaak_status)).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()
        eigenschap_data = self.client.get(
            reverse(eigenschap, kwargs={"zaak_uuid": zaak.uuid})
        ).json()

        # The detail responses also include the _expand attribute, but the list response
        # only has a _expand attribute at the root level (no _expand nested inside _expand)
        del zaak_data["_expand"]
        del hoofdzaak_data["_expand"]

        response = self.client.get(
            zaak_url,
            {"expand": "hoofdzaak,zaaktype,status,resultaat,eigenschappen"},
            **ZAAK_READ_KWARGS,
        )

        data = response.json()
        expected_results = {
            **zaak_data,
            "_expand": {
                "zaaktype": zaaktype_data,
                "hoofdzaak": hoofdzaak_data,
                "eigenschappen": [eigenschap_data],
                "status": status_data,
                "resultaat": resultaat_data,
            },
        }
        self.assertEqual(data, expected_results)


@tag("expand-authorization")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZakenIncludePermissionsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = False
    zaak_url = reverse_lazy("zaak-list")
    zaaktype_url = reverse_lazy("zaaktype-list")

    @classmethod
    def setUpTestData(cls):
        cls.catalogus = CatalogusFactory.create()
        cls.zaaktype = ZaakTypeFactory.create(concept=False, catalogus=cls.catalogus)
        cls.zaaktype_url = reverse(cls.zaaktype)
        super().setUpTestData()

    def test_zaken_list_expand_zaken_resource(self):
        # No permissions for the zaken resource
        self.autorisatie.scopes = []
        self.autorisatie.save()
        response = self.client.get(
            self.zaak_url, {"expand": "status"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaken is NOT allowed with SCOPE_ZAKEN_CREATE
        self.autorisatie.scopes = [SCOPE_ZAKEN_CREATE]
        self.autorisatie.save()
        response = self.client.get(
            self.zaak_url, {"expand": "status"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read the zaken resource with expand a zaken resource (status) is allowed with SCOPE_ZAKEN_ALLES_LEZEN
        self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
        self.autorisatie.save()
        response = self.client.get(
            self.zaak_url, {"expand": "status"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zaken_list_expand_catalogi_resource(self):
        # No permissions for the catalogi and zaken resource
        self.autorisatie.scopes = []
        self.autorisatie.save()

        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(
            self.zaak_url, {"expand": "zaaktype"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaken is NOT allowed with SCOPE_ZAKEN_CREATE
        self.autorisatie.scopes = [SCOPE_ZAKEN_CREATE]
        self.autorisatie.save()
        response = self.client.get(
            self.zaak_url, {"expand": "zaaktype"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaken is allowed with SCOPE_ZAKEN_ALLES_LEZEN
        self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
        self.autorisatie.save()
        response = self.client.get(self.zaak_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read zaaktypen is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaken with zaaktypen expand is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(
            self.zaak_url, {"expand": "zaaktype"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add a Catalogi authorization with a write-only scope.
        catalogi_auth = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.ztc,
            scopes=[SCOPE_CATALOGI_WRITE],
        )

        # Read zaaktypen is NOT allowed with SCOPE_CATALOGI_WRITE
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Grant Catalogi read permission.
        catalogi_auth.scopes = [SCOPE_CATALOGI_READ]
        catalogi_auth.save()

        # Read zaaktypen is allowed with SCOPE_CATALOGI_READ
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read zaken with zaaktypen expand is allowed with SCOPE_ZAKEN_ALLES_LEZEN and SCOPE_CATALOGI_READ
        response = self.client.get(
            self.zaak_url,
            {"expand": "zaaktype"},
            **ZAAK_READ_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zaak_detail_expand_catalogi_resource(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_detail = reverse(zaak)

        # No permissions for the catalogi and zaken resource
        self.autorisatie.scopes = []
        self.autorisatie.save()
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(
            zaak_detail, {"expand": "zaaktype"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaak is allowed with SCOPE_ZAKEN_ALLES_LEZEN
        self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
        self.autorisatie.save()
        response = self.client.get(zaak_detail, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read zaaktypen is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaak with zaaktypen expand is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(
            zaak_detail, {"expand": "zaaktype"}, **ZAAK_READ_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add a Catalogi authorization with a write-only scope.
        catalogi_auth = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.ztc,
            scopes=[SCOPE_CATALOGI_WRITE],
        )

        # Read zaaktypen is NOT allowed with SCOPE_CATALOGI_WRITE
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Grant Catalogi read permission.
        catalogi_auth.scopes = [SCOPE_CATALOGI_READ]
        catalogi_auth.save()

        # Read zaaktypen is allowed with SCOPE_CATALOGI_READ
        response = self.client.get(self.zaaktype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read zaak with zaaktypen expand is allowed with SCOPE_ZAKEN_ALLES_LEZEN and SCOPE_CATALOGI_READ
        response = self.client.get(
            zaak_detail,
            {"expand": "zaaktype"},
            **ZAAK_READ_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zaken_list_expand_nested_catalogi_resource(self):
        resultaattype_url = reverse("resultaattype-list")

        # Read zaken is allowed with SCOPE_ZAKEN_ALLES_LEZEN
        self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
        self.autorisatie.save()
        response = self.client.get(self.zaak_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read resultaattype is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(resultaattype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Read zaken with resultaat.resultaattype expand is NOT allowed with SCOPE_ZAKEN_ALLES_LEZEN
        response = self.client.get(
            self.zaak_url,
            {"expand": "resultaat,resultaat.resultaattype"},
            **ZAAK_READ_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add a Catalogi authorization with a write-only scope.
        catalogi_auth = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.ztc,
            scopes=[SCOPE_CATALOGI_WRITE],
        )

        # Read resultaattype is NOT allowed with SCOPE_CATALOGI_WRITE
        response = self.client.get(resultaattype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Grant Catalogi read permission.
        catalogi_auth.scopes = [SCOPE_CATALOGI_READ]
        catalogi_auth.save()

        # Read resultaattype is allowed with SCOPE_CATALOGI_READ
        response = self.client.get(resultaattype_url, **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Read zaken with resultaattype expand is allowed with SCOPE_ZAKEN_ALLES_LEZEN and SCOPE_CATALOGI_READ
        response = self.client.get(
            self.zaak_url,
            {"expand": "resultaat,resultaat.resultaattype"},
            **ZAAK_READ_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag("external-urls", "expand")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZakenExternalIncludeTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    url = reverse_lazy("zaken:zaak-list")

    def test_zaak_list_include(self):
        """
        Test if related resources that are external can be included
        """
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)
        zaak = ZaakFactory.create(zaaktype=zaaktype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()

        with requests_mock.Mocker() as m:
            m.get(zaaktype, json=zaaktype_data)

            response = self.client.get(
                self.url,
                {"expand": "zaaktype"},
                **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [{**zaak_data, "_expand": {"zaaktype": zaaktype_data}}]
        self.assertEqual(data, expected_results)

    def test_zaak_list_include_nested(self):
        """
        Test if nested related resources that are external can be included
        """
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        resultaattype = "https://externe.catalogus.nl/api/v1/resultaattypen/9a784c52-456c-4864-8841-9b94e01e778f"
        resultaattype_data = get_resultaattype_response(resultaattype, zaaktype)

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        resultaat = ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()
        resultaat_data = self.client.get(reverse(resultaat)).json()

        with requests_mock.Mocker() as m:
            m.get(resultaattype, json=resultaattype_data)
            response = self.client.get(
                self.url,
                {"expand": "resultaat,resultaat.resultaattype"},
                **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_result = [
            {
                **zaak_data,
                "_expand": {
                    "resultaat": {
                        **resultaat_data,
                        "_expand": {"resultaattype": resultaattype_data},
                    }
                },
            }
        ]
        self.assertEqual(data, expected_result)

    def test_zaak_list_include_cache(self):
        """
        test that the external data are cached and the requests are not repeated
        """
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)
        ZaakFactory.create_batch(5, zaaktype=zaaktype)

        with requests_mock.Mocker() as m:
            m.get(zaaktype, json=zaaktype_data)

            response = self.client.get(
                self.url,
                {"expand": "zaaktype"},
                **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(m.request_history), 1)

    def test_connection_error(self):
        """
        test that connection errors for external urls don't crash the response
        """
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaak = ZaakFactory.create(zaaktype=zaaktype)

        zaak_data = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS).json()

        with requests_mock.Mocker() as m:
            m.get(zaaktype, status_code=500)

            response = self.client.get(
                self.url,
                {"expand": "zaaktype"},
                **ZAAK_READ_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [{**zaak_data, "_expand": {}}]
        self.assertEqual(data, expected_results)
