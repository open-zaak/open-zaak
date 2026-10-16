# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import connection
from django.test.utils import CaptureQueriesContext

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from ..models import Catalogus
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)


class CatalogusAPITests(APITestCase):
    maxDiff = None

    def test_get_list(self):
        """Retrieve a list of `Catalog` objects."""
        response = self.client.get(self.catalogus_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)

    def test_get_detail(self):
        """Retrieve the details of a single `Catalog` object."""
        response = self.client.get(self.catalogus_detail_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "domein": self.catalogus.domein,
            "url": "http://testserver{}".format(self.catalogus_detail_url),
            "contactpersoonBeheerTelefoonnummer": "0612345678",
            "rsin": self.catalogus.rsin,
            "contactpersoonBeheerNaam": self.catalogus.contactpersoon_beheer_naam,
            "contactpersoonBeheerEmailadres": self.catalogus.contactpersoon_beheer_emailadres,
            "informatieobjecttypen": [],
            "informatieobjecttypeOmschrijving": [],
            "zaaktypen": [],
            "besluittypen": [],
            "besluittypeOmschrijving": [],
            "naam": self.catalogus.naam,
            "versie": "",
            "begindatumVersie": None,
            "_expand": {},
        }
        self.assertEqual(response.json(), expected)

    def test_get_detail_besluittype_and_informatieobjecttype_omschrijving(self):
        catalogus = CatalogusFactory.create()
        besluittype1 = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype2 = BesluitTypeFactory.create(catalogus=catalogus)
        iotype1 = InformatieObjectTypeFactory.create(catalogus=catalogus)
        iotype2 = InformatieObjectTypeFactory.create(catalogus=catalogus)
        BesluitTypeFactory.create()
        InformatieObjectTypeFactory.create()

        response = self.client.get(reverse(catalogus))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertCountEqual(
            data["besluittypeOmschrijving"],
            [besluittype1.omschrijving, besluittype2.omschrijving],
        )
        self.assertCountEqual(
            data["informatieobjecttypeOmschrijving"],
            [iotype1.omschrijving, iotype2.omschrijving],
        )
        self.assertEqual(len(data["besluittypen"]), 2)
        self.assertEqual(len(data["informatieobjecttypen"]), 2)

    def test_omschrijving_fields_are_read_only(self):
        catalogus = CatalogusFactory.create()
        BesluitTypeFactory.create(catalogus=catalogus, omschrijving="besluittype")

        response = self.client.patch(
            reverse(catalogus),
            {
                "besluittypeOmschrijving": ["other"],
                "informatieobjecttypeOmschrijving": ["other"],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["besluittypeOmschrijving"], ["besluittype"])
        self.assertEqual(data["informatieobjecttypeOmschrijving"], [])

    def test_get_list_omschrijving_does_not_add_queries_per_catalogus(self):
        def count_list_queries() -> int:
            with CaptureQueriesContext(connection) as ctx:
                response = self.client.get(self.catalogus_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return len(ctx)

        count_list_queries()
        baseline = count_list_queries()

        for _ in range(3):
            catalogus = CatalogusFactory.create()
            BesluitTypeFactory.create(catalogus=catalogus)
            InformatieObjectTypeFactory.create(catalogus=catalogus)

        self.assertEqual(count_list_queries(), baseline)

    def test_create_catalogus(self):
        data = {
            "domein": "TEST",
            "contactpersoonBeheerTelefoonnummer": "0612345679",
            "rsin": "100000009",
            "contactpersoonBeheerNaam": "test",
            "contactpersoonBeheerEmailadres": "test@test.com",
        }

        response = self.client.post(self.catalogus_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        catalog = Catalogus.objects.get(domein="TEST")

        self.assertEqual(catalog.rsin, "100000009")

    def test_update_catalogus(self):
        catalogus_url = reverse(self.catalogus)

        data = {
            "domein": "TEST",
            "contactpersoonBeheerTelefoonnummer": "0698765432",
            "rsin": "517439943",
            "contactpersoonBeheerNaam": "aangepast",
            "contactpersoonBeheerEmailadres": "aangepast@test.com",
        }

        response = self.client.put(catalogus_url, data)
        response_data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data["domein"], "TEST")

        self.catalogus.refresh_from_db()

        self.assertEqual(self.catalogus.domein, "TEST")
        self.assertEqual(
            self.catalogus.contactpersoon_beheer_telefoonnummer,
            "0698765432",
        )
        self.assertEqual(self.catalogus.rsin, "517439943")
        self.assertEqual(
            self.catalogus.contactpersoon_beheer_naam,
            "aangepast",
        )
        self.assertEqual(
            self.catalogus.contactpersoon_beheer_emailadres,
            "aangepast@test.com",
        )

    def test_partial_update_catalogus(self):
        catalogus_url = reverse(self.catalogus)

        response = self.client.patch(
            catalogus_url,
            {"naam": "aangepast"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["naam"], "aangepast")

        self.catalogus.refresh_from_db()

        self.assertEqual(self.catalogus.naam, "aangepast")

    def test_get_detail_expand_zaaktypen(self):
        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)

        response = self.client.get(
            reverse(catalogus),
            {"expand": "zaaktypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["zaaktypen"]), 1)
        self.assertEqual(
            data["_expand"]["zaaktypen"][0]["url"],
            f"http://testserver{reverse(zaaktype)}",
        )

    def test_get_detail_expand_besluittypen(self):
        catalogus = CatalogusFactory.create()
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)

        response = self.client.get(
            reverse(catalogus),
            {"expand": "besluittypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["besluittypen"]), 1)
        self.assertEqual(
            data["_expand"]["besluittypen"][0]["url"],
            f"http://testserver{reverse(besluittype)}",
        )

    def test_get_detail_expand_informatieobjecttypen(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        response = self.client.get(
            reverse(catalogus),
            {"expand": "informatieobjecttypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["informatieobjecttypen"]), 1)
        self.assertEqual(
            data["_expand"]["informatieobjecttypen"][0]["url"],
            f"http://testserver{reverse(informatieobjecttype)}",
        )

    def test_get_detail_expand_nested_not_supported(self):
        catalogus = CatalogusFactory.create()

        response = self.client.get(
            reverse(catalogus),
            {"expand": "zaaktypen.catalogus"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = get_validation_errors(response, "expand")
        self.assertEqual(
            errors["reason"],
            "Selecteer een geldige keuze. zaaktypen.catalogus is geen beschikbare keuze.",
        )


class CatalogusFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_domein_exact(self):
        catalogus1 = CatalogusFactory.create(domein="ABC")
        CatalogusFactory.create(domein="DEF")

        response = self.client.get(self.catalogus_list_url, {"domein": "ABC"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(catalogus1)}")

    def test_filter_domein_in(self):
        catalogus1 = CatalogusFactory.create(domein="ABC")
        CatalogusFactory.create(domein="DEF")

        response = self.client.get(self.catalogus_list_url, {"domein__in": "ABC,AAA"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(catalogus1)}")

    def test_filter_rsin_exact(self):
        catalogus1 = CatalogusFactory.create(rsin="100000009")
        CatalogusFactory.create(rsin="100000020")

        response = self.client.get(self.catalogus_list_url, {"rsin": "100000009"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(catalogus1)}")

    def test_filter_rsin_in(self):
        catalogus1 = CatalogusFactory.create(rsin="100000009")
        CatalogusFactory.create(rsin="100000022")

        response = self.client.get(
            self.catalogus_list_url, {"rsin__in": "100000009,100000010"}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(catalogus1)}")

    def test_validate_unknown_query_params(self):
        CatalogusFactory.create_batch(2)
        url = reverse(Catalogus)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class CatalogusPaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        response = self.client.get(self.catalogus_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        response = self.client.get(self.catalogus_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        CatalogusFactory.create_batch(9)

        response = self.client.get(self.catalogus_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"],
            f"http://testserver{self.catalogus_list_url}?page=2&pageSize=5",
        )
