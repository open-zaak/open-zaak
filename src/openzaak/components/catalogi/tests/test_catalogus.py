# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from vng_api_common.tests import get_validation_errors

from openzaak.utils.urls import reverse

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
    NAMESPACE = "catalogi"
    INFORMATIEOBJECTTYPE_NAMESPACE = "catalogi"

    def test_get_list(self):
        """Retrieve a list of `Catalog` objects."""
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)

    def test_get_detail(self):
        """Retrieve the details of a single `Catalog` object."""
        catalogus_detail_url = reverse(self.catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_detail_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "domein": self.catalogus.domein,
            "url": "http://testserver{}".format(catalogus_detail_url),
            "contactpersoonBeheerTelefoonnummer": "0612345678",
            "rsin": self.catalogus.rsin,
            "contactpersoonBeheerNaam": self.catalogus.contactpersoon_beheer_naam,
            "contactpersoonBeheerEmailadres": self.catalogus.contactpersoon_beheer_emailadres,
            "informatieobjecttypen": [],
            "zaaktypen": [],
            "besluittypen": [],
            "naam": self.catalogus.naam,
            "versie": "",
            "begindatumVersie": None,
            "_expand": {},
        }
        self.assertEqual(response.json(), expected)

    def test_create_catalogus(self):
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)
        data = {
            "domein": "TEST",
            "contactpersoonBeheerTelefoonnummer": "0612345679",
            "rsin": "100000009",
            "contactpersoonBeheerNaam": "test",
            "contactpersoonBeheerEmailadres": "test@test.com",
        }

        response = self.client.post(catalogus_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        catalog = Catalogus.objects.get(domein="TEST")

        self.assertEqual(catalog.rsin, "100000009")

    def test_update_catalogus(self):
        catalogus_url = reverse(self.catalogus, namespace=self.NAMESPACE)

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
        catalogus_url = reverse(self.catalogus, namespace=self.NAMESPACE)

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
            reverse(catalogus, namespace=self.NAMESPACE),
            {"expand": "zaaktypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["zaaktypen"]), 1)
        self.assertEqual(
            data["_expand"]["zaaktypen"][0]["url"],
            f"http://testserver{reverse(zaaktype, namespace=self.NAMESPACE)}",
        )

    def test_get_detail_expand_besluittypen(self):
        catalogus = CatalogusFactory.create()
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)

        response = self.client.get(
            reverse(catalogus, namespace=self.NAMESPACE),
            {"expand": "besluittypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["besluittypen"]), 1)
        self.assertEqual(
            data["_expand"]["besluittypen"][0]["url"],
            f"http://testserver{reverse(besluittype, namespace=self.NAMESPACE)}",
        )

    def test_get_detail_expand_informatieobjecttypen(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        response = self.client.get(
            reverse(catalogus, namespace=self.NAMESPACE),
            {"expand": "informatieobjecttypen"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["_expand"]["informatieobjecttypen"]), 1)
        self.assertEqual(
            data["_expand"]["informatieobjecttypen"][0]["url"],
            f"http://testserver{reverse(informatieobjecttype, namespace=self.INFORMATIEOBJECTTYPE_NAMESPACE)}",
        )

    def test_get_detail_expand_nested_not_supported(self):
        catalogus = CatalogusFactory.create()

        response = self.client.get(
            reverse(catalogus, namespace=self.NAMESPACE),
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
    NAMESPACE = "catalogi"

    def test_filter_domein_exact(self):
        catalogus1 = CatalogusFactory.create(domein="ABC")
        CatalogusFactory.create(domein="DEF")
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url, {"domein": "ABC"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse(catalogus1, namespace=self.NAMESPACE)}",
        )

    def test_filter_domein_in(self):
        catalogus1 = CatalogusFactory.create(domein="ABC")
        CatalogusFactory.create(domein="DEF")
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url, {"domein__in": "ABC,AAA"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse(catalogus1, namespace=self.NAMESPACE)}",
        )

    def test_filter_rsin_exact(self):
        catalogus1 = CatalogusFactory.create(rsin="100000009")
        CatalogusFactory.create(rsin="100000020")
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url, {"rsin": "100000009"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse(catalogus1, namespace=self.NAMESPACE)}",
        )

    def test_filter_rsin_in(self):
        catalogus1 = CatalogusFactory.create(rsin="100000009")
        CatalogusFactory.create(rsin="100000022")
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(
            catalogus_list_url, {"rsin__in": "100000009,100000010"}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"],
            f"http://testserver{reverse(catalogus1, namespace=self.NAMESPACE)}",
        )

    def test_validate_unknown_query_params(self):
        CatalogusFactory.create_batch(2)
        url = reverse(Catalogus)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class CatalogusPaginationTestCase(APITestCase):
    maxDiff = None
    NAMESPACE = "catalogi"

    def test_pagination_default(self):
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        CatalogusFactory.create_batch(9)
        catalogus_list_url = reverse(Catalogus, namespace=self.NAMESPACE)

        response = self.client.get(catalogus_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"],
            f"http://testserver{catalogus_list_url}?page=2&pageSize=5",
        )
