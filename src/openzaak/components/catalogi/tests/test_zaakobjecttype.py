# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from datetime import date

from django.test import override_settings

from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..models import ZaakObjectType
from .base import APITestCase
from .factories import StatusTypeFactory, ZaakObjectTypeFactory, ZaakTypeFactory


class ZaakObjectTypeAPITests(APITestCase):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    def test_list_zaakobjecttypen_default_definitief(self):
        ZaakObjectTypeFactory.create(zaaktype__concept=True)
        zaakobjecttype2 = ZaakObjectTypeFactory.create(zaaktype__concept=False)
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        zaakobjecttype2_url = reverse(
            "zaakobjecttype-detail", kwargs={"uuid": zaakobjecttype2.uuid}
        )

        response = self.client.get(zaakobjecttype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{zaakobjecttype2_url}")

    def test_get_zaakobjecttype(self):
        statustype = StatusTypeFactory.create(zaaktype__catalogus=self.catalogus)
        zaakobjecttype = ZaakObjectTypeFactory.create(
            ander_objecttype=False,
            relatie_omschrijving="test description",
            zaaktype=statustype.zaaktype,
            objecttype="http://example.org/objecttypen/1",
            statustype=statustype,
            datum_begin_geldigheid=date(2023, 1, 1),
            datum_einde_geldigheid=date(2023, 12, 1),
        )
        zaakobjecttype_detail_url = reverse(zaakobjecttype)

        response = self.client.get(zaakobjecttype_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            "url": f"http://testserver{zaakobjecttype_detail_url}",
            "zaaktype": f"http://testserver{reverse(zaakobjecttype.zaaktype)}",
            "zaaktypeIdentificatie": zaakobjecttype.zaaktype.identificatie,
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "resultaattypen": [],
            "statustype": f"http://testserver{reverse(statustype)}",
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
            "beginObject": "2023-01-01",
            "eindeObject": "2023-12-01",
        }
        self.assertEqual(expected, response.json())

    def test_create_zaakobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
        }

        response = self.client.post(zaakobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaakobjecttype = ZaakObjectType.objects.get()

        self.assertEqual(zaakobjecttype.objecttype, "http://example.org/objecttypen/1")
        self.assertEqual(zaakobjecttype.zaaktype, zaaktype)
        self.assertFalse(zaakobjecttype.ander_objecttype)
        self.assertEqual(zaakobjecttype.relatie_omschrijving, "test description")
        self.assertEqual(zaakobjecttype.datum_begin_geldigheid, date(2023, 1, 1))
        self.assertEqual(zaakobjecttype.datum_einde_geldigheid, date(2023, 12, 1))

    def test_create_zaakobjecttype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
        }

        response = self.client.post(zaakobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_create_zaakobjecttype_with_statustype(self):
        zaaktype = ZaakTypeFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
            "statustype": f"http://testserver{reverse(statustype)}",
        }

        response = self.client.post(zaakobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaakobjecttype = ZaakObjectType.objects.get()
        self.assertEqual(zaakobjecttype.statustype, statustype)

    def test_create_zaakobjecttype_with_statustype_another_zaaktype_fail(self):
        zaaktype = ZaakTypeFactory.create()
        statustype = StatusTypeFactory.create()
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
            "statustype": f"http://testserver{reverse(statustype)}",
        }

        response = self.client.post(zaakobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-zaaktype")

    def test_create_zaakobject_with_end_date_before_start_date(self):
        zaaktype = ZaakTypeFactory.create()
        zaakobjecttype_list_url = reverse("zaakobjecttype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "test description",
            "beginGeldigheid": "2023-12-01",
            "eindeGeldigheid": "2023-01-01",
        }

        response = self.client.post(zaakobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "date-mismatch")

    def test_delete_zaakobjecttype(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        zaakobjecttype_url = reverse(zaakobjecttype)

        response = self.client.delete(zaakobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakObjectType.objects.filter(id=zaakobjecttype.id))

    def test_delete_zaakobjecttype_fail_not_concept_zaaktype(self):
        zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype__concept=False)
        zaakobjecttype_url = reverse(zaakobjecttype)

        response = self.client.delete(zaakobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_update_zaakobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=zaaktype, relatie_omschrijving="old"
        )
        zaakobjecttype_url = reverse(zaakobjecttype)
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "new",
        }

        response = self.client.put(zaakobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaakobjecttype.refresh_from_db()
        self.assertEqual(zaakobjecttype.relatie_omschrijving, "new")

    def test_update_zaakobjecttype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=zaaktype, relatie_omschrijving="old"
        )
        zaakobjecttype_url = reverse(zaakobjecttype)
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "anderObjecttype": False,
            "objecttype": "http://example.org/objecttypen/1",
            "relatieOmschrijving": "new",
        }

        response = self.client.put(zaakobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_patch_zaakobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=zaaktype, relatie_omschrijving="old"
        )
        zaakobjecttype_url = reverse(zaakobjecttype)

        response = self.client.patch(zaakobjecttype_url, {"relatieOmschrijving": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaakobjecttype.refresh_from_db()
        self.assertEqual(zaakobjecttype.relatie_omschrijving, "new")

    def test_patch_zaakobjecttype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=zaaktype, relatie_omschrijving="old"
        )
        zaakobjecttype_url = reverse(zaakobjecttype)

        response = self.client.patch(zaakobjecttype_url, {"relatieOmschrijving": "new"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)


class ZaakObjectTypeFilterAPITests(APITestCase):
    url = reverse_lazy("zaakobjecttype-list")

    def test_filter_ander_objecttype(self):
        zaakobjecttype1 = ZaakObjectTypeFactory.create(
            ander_objecttype=True, zaaktype__concept=False
        )
        ZaakObjectTypeFactory.create(ander_objecttype=False, zaaktype__concept=False)

        response = self.client.get(self.url, {"anderObjecttype": True})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaakobjecttype1)}")

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_filter_catalogus(self):
        zaakobjecttype1 = ZaakObjectTypeFactory.create(
            zaaktype__catalogus=self.catalogus, zaaktype__concept=False
        )
        ZaakObjectTypeFactory.create(zaaktype__concept=False)

        response = self.client.get(
            self.url,
            {"catalogus": f"http://testserver.com{self.catalogus_detail_url}"},
            headers={"host": "testserver.com"},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"], f"http://testserver.com{reverse(zaakobjecttype1)}"
        )

    def test_filter_objecttype(self):
        zaakobjecttype1 = ZaakObjectTypeFactory.create(
            objecttype="http://example.org/objecttypen/1", zaaktype__concept=False
        )
        ZaakObjectTypeFactory.create(
            objecttype="http://example.org/objecttypen/2", zaaktype__concept=False
        )

        response = self.client.get(
            self.url, {"objecttype": "http://example.org/objecttypen/1"}
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaakobjecttype1)}")

    def test_filter_relatie_omschrijving(self):
        zaakobjecttype1 = ZaakObjectTypeFactory.create(
            relatie_omschrijving="some", zaaktype__concept=False
        )
        ZaakObjectTypeFactory.create(
            relatie_omschrijving="other", zaaktype__concept=False
        )

        response = self.client.get(self.url, {"relatieOmschrijving": "some"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaakobjecttype1)}")

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_filter_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaakobjecttype1 = ZaakObjectTypeFactory.create(zaaktype=zaaktype)
        ZaakObjectTypeFactory.create(zaaktype__concept=False)

        response = self.client.get(
            self.url,
            {"zaaktype": f"http://testserver.com{reverse(zaaktype)}"},
            headers={"host": "testserver.com"},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"], f"http://testserver.com{reverse(zaakobjecttype1)}"
        )

    def test_filter_zaaktype_identificatie(self):
        zaakobjecttype1 = ZaakObjectTypeFactory.create(
            zaaktype__identificatie="some", zaaktype__concept=False
        )
        ZaakObjectTypeFactory.create(
            zaaktype__identificatie="other", zaaktype__concept=False
        )

        response = self.client.get(self.url, {"zaaktypeIdentificatie": "some"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaakobjecttype1)}")

    def test_filter_geldigheid(self):
        zaakobjecttype = ZaakObjectTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            zaaktype__concept=False,
        )
        ZaakObjectTypeFactory.create(
            datum_begin_geldigheid=date(2020, 2, 1), zaaktype__concept=False
        )

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(zaakobjecttype)}")


class ZaakObjectTypePaginationTests(APITestCase):
    url = reverse_lazy("zaakobjecttype-list")

    def test_pagination_default(self):
        ZaakObjectTypeFactory.create_batch(2, zaaktype__concept=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakObjectTypeFactory.create_batch(2, zaaktype__concept=False)

        response = self.client.get(self.url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        ZaakObjectTypeFactory.create_batch(10, zaaktype__concept=False)

        response = self.client.get(self.url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["next"], f"http://testserver{self.url}?page=2&pageSize=5")
