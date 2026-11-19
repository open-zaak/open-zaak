# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors

from openzaak.components.autorisaties.models import Autorisatie
from openzaak.components.catalogi.api.scopes import (
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from openzaak.components.catalogi.tests.factories import (
    ZaakTypeFactory,
)
from openzaak.components.catalogi.tests.factories.resultaattype import (
    ResultaatTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.expansion import EXPAND_QUERY_PARAM
from openzaak.utils.urls import reverse, reverse_lazy

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE
from .factories import (
    ResultaatFactory,
    ZaakFactory,
)
from .utils import (
    ZAAK_READ_KWARGS,
    get_operation_url,
)


@override_settings(ALLOWED_HOSTS=["testserver"])
class ResultaatListTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("resultaat_create")

    def test_pagination_pagesize_param(self):
        ResultaatFactory.create_batch(10)

        response = self.client.get(self.list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )


@tag("expand")
class ResultatenExpandTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    url = reverse_lazy("zaken:resultaat-list")

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.resultaattype = ResultaatTypeFactory.create(zaaktype=cls.zaaktype)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)
        cls.resultaat = ResultaatFactory.create(
            zaak=cls.zaak, resultaattype=cls.resultaattype
        )

        super().setUpTestData()

    def test_resultaat_include_all_resources_with_query_count(self):
        """Return zaak, zaaktype and resultaattype together."""
        resultaat_data = self.client.get(reverse(self.resultaat)).json()
        zaak_data = self.client.get(reverse(self.zaak), **ZAAK_READ_KWARGS).json()
        zaaktype_data = self.client.get(reverse(self.zaaktype)).json()
        resultaattype_data = self.client.get(reverse(self.resultaattype)).json()

        # The detail responses also include the _expand attribute, but the list response
        # only has a _expand attribute at the root level (no _expand nested inside _expand)
        del zaak_data["_expand"]
        del zaaktype_data["_expand"]
        del resultaattype_data["_expand"]

        expected = {
            **resultaat_data,
            "_expand": {
                "zaak": {**zaak_data, "_expand": {"zaaktype": zaaktype_data}},
                "resultaattype": resultaattype_data,
            },
        }

        with self.assertNumQueries(29):
            response = self.client.get(
                self.url,
                {"expand": "zaak,zaak.zaaktype,resultaattype"},
                **ZAAK_READ_KWARGS,
            )
            response_data = response.json()

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response_data["results"], [expected])

    def test_resultaat_include_each_resource(self):
        """Request each direct relation without including the others."""
        resultaat_data = self.client.get(reverse(self.resultaat)).json()
        zaak_data = self.client.get(reverse(self.zaak), **ZAAK_READ_KWARGS).json()
        resultaattype_data = self.client.get(reverse(self.resultaattype)).json()

        # The detail responses also include the _expand attribute, but the list response
        # only has a _expand attribute at the root level (no _expand nested inside _expand)
        del zaak_data["_expand"]
        del resultaattype_data["_expand"]

        expected_expansions = {
            "zaak": {"zaak": zaak_data},
            "resultaattype": {"resultaattype": resultaattype_data},
        }
        for expand, expected_expand in expected_expansions.items():
            with self.subTest(expand=expand):
                response = self.client.get(
                    self.url, {"expand": expand}, **ZAAK_READ_KWARGS
                )
                response_data = response.json()

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                expected = {**resultaat_data, "_expand": expected_expand}

                self.assertEqual(response_data["results"], [expected])

    def test_resultaat_list_no_expand(self):
        """Keep an empty _expand when the parameter is absent or empty."""
        resultaat_data = self.client.get(reverse(self.resultaat)).json()

        response = self.client.get(self.url, {"expand": ""}, **ZAAK_READ_KWARGS)
        response_data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data["results"], [{**resultaat_data, "_expand": {}}])

    def test_resultaat_retrieve_no_expand(self):
        """Keep an empty _expand when no expand param."""
        response = self.client.get(reverse(self.resultaat))
        response_data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data["_expand"], {})

    def test_invalid_expansion(self):
        for expand in ("unknown", "zaak.unknown", "zaak,unknown"):
            with self.subTest(expand=expand):
                response = self.client.get(
                    self.url, {"expand": expand}, **ZAAK_READ_KWARGS
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                error = get_validation_errors(response, "expand")
                self.assertEqual(error["code"], "invalid_choice")

    def test_resultaat_list_nested_expansion_requires_parent(self):
        """A nested path only adds data when its parent is also requested."""
        resultaat_data = self.client.get(reverse(self.resultaat)).json()

        response = self.client.get(
            self.url, {"expand": "zaak.zaaktype"}, **ZAAK_READ_KWARGS
        )
        response_data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data["results"], [{**resultaat_data, "_expand": {}}])


@tag("expand-authorization")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ResultatenIncludePermissionsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = False

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)
        cls.resultaat = ResultaatFactory.create(zaak=cls.zaak)
        cls.list_url = reverse("zaken:resultaat-list")
        cls.detail_url = reverse(cls.resultaat)
        super().setUpTestData()

    def _test_expand_auth(self, params: dict[str, str]):
        """Check the expanded resources auth for both list and detail requests"""

        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                expanded_field = params.get(EXPAND_QUERY_PARAM, "").split(",")[0]

                # No scopes access is denied
                self.autorisatie.scopes = []
                self.autorisatie.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # SCOPE_ZAKEN_CREATE does not grant access
                self.autorisatie.scopes = [SCOPE_ZAKEN_CREATE]
                self.autorisatie.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # SCOPE_ZAKEN_ALLES_LEZEN permits access to its own resource
                self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
                self.autorisatie.save()
                response = self.client.get(url, {"expand": "zaak"}, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # Catalogi expansion requires SCOPE_CATALOGI_READ
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # Only SCOPE_CATALOGI_WRITE is insufficient
                catalogi_auth = Autorisatie.objects.create(
                    applicatie=self.applicatie,
                    component=ComponentTypes.ztc,
                    scopes=[SCOPE_CATALOGI_WRITE],
                )
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # Adding SCOPE_CATALOGI_READ access permits the expansion
                catalogi_auth.scopes = [SCOPE_CATALOGI_READ]
                catalogi_auth.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                catalogi_auth.delete()  # remove auth for the next use

                data = response.json()
                if url == self.list_url:
                    data = data["results"][0]
                self.assertIn(expanded_field, data["_expand"])

    def test_expand_resultaattype_permissions(self):
        """Expanding resultaattype requires SCOPE_CATALOGI_READ"""
        params = {"expand": "resultaattype"}
        self._test_expand_auth(params)

    def test_expand_zaak_zaaktype_permissions(self):
        """Expanding zaak,zaak.zaaktype requires SCOPE_CATALOGI_READ"""
        params = {"expand": "zaak,zaak.zaaktype"}
        self._test_expand_auth(params)
