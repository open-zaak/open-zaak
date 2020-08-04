# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..models import StatusType
from .base import APITestCase
from .factories import RolTypeFactory, StatusTypeFactory, ZaakTypeFactory
from .utils import get_operation_url


class StatusTypeAPITests(APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    def test_get_list_default_definitief(self):
        StatusTypeFactory.create(zaaktype__concept=True)
        statustype2 = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")
        statustype2_url = reverse(
            "statustype-detail", kwargs={"uuid": statustype2.uuid}
        )

        response = self.client.get(statustype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{statustype2_url}")

    def test_get_detail(self):
        statustype = StatusTypeFactory.create(
            statustype_omschrijving="Besluit genomen",
            zaaktype__catalogus=self.catalogus,
        )
        statustype_detail_url = reverse(
            "statustype-detail", kwargs={"uuid": statustype.uuid}
        )
        zaaktype = statustype.zaaktype
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        response = self.client.get(statustype_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            "url": "http://testserver{}".format(statustype_detail_url),
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": statustype.statustypevolgnummer,
            "isEindstatus": True,
            "informeren": False,
        }

        self.assertEqual(expected, response.json())

    def test_create_statustype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        statustype_list_url = reverse("statustype-list")
        data = {
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
        }
        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        statustype = StatusType.objects.get()

        self.assertEqual(statustype.statustype_omschrijving, "Besluit genomen")
        self.assertEqual(statustype.zaaktype, zaaktype)

    def test_create_statustype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        statustype_list_url = reverse("statustype-list")
        data = {
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
        }
        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_delete_statustype(self):
        statustype = StatusTypeFactory.create()
        statustype_url = reverse("statustype-detail", kwargs={"uuid": statustype.uuid})

        response = self.client.delete(statustype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StatusType.objects.filter(id=statustype.id))

    def test_delete_statustype_fail_not_concept_zaaktype(self):
        statustype = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_url = reverse("statustype-detail", kwargs={"uuid": statustype.uuid})

        response = self.client.delete(statustype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_is_eindstatus(self):
        zaaktype = ZaakTypeFactory.create()

        RolTypeFactory.create(zaaktype=zaaktype)

        statustype_1 = StatusTypeFactory.create(
            zaaktype=zaaktype, statustypevolgnummer=1
        )
        statustype_2 = StatusTypeFactory.create(
            zaaktype=zaaktype, statustypevolgnummer=2
        )

        # Volgnummer 1
        url = get_operation_url(
            "statustype_read",
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
            uuid=statustype_1.uuid,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertFalse(response_data["isEindstatus"])

        # Volgnummer 2
        url = get_operation_url(
            "statustype_read",
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
            uuid=statustype_2.uuid,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertTrue(response_data["isEindstatus"])

    def test_update_statustype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)

        data = {
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
        }

        response = self.client.put(statustype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

        statustype.refresh_from_db()
        self.assertEqual(statustype.statustype_omschrijving, "aangepast")

    def test_update_statustype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)

        data = {
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
        }

        response = self.client.put(statustype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_update_statustype_add_relation_to_non_concept_zaaktype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        statustype = StatusTypeFactory.create()
        statustype_url = reverse(statustype)

        data = {
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
        }

        response = self.client.put(statustype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_partial_update_statustype(self):
        zaaktype = ZaakTypeFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)

        response = self.client.patch(statustype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

        statustype.refresh_from_db()
        self.assertEqual(statustype.statustype_omschrijving, "aangepast")

    def test_partial_update_statustype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)

        response = self.client.patch(statustype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)

    def test_partial_update_statustype_add_relation_to_non_concept_zaaktype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        statustype = StatusTypeFactory.create()
        statustype_url = reverse(statustype)

        response = self.client.patch(statustype_url, {"zaaktype": zaaktype_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ZaakTypeConceptValidator.code)


class StatusTypeFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_statustype_status_alles(self):
        StatusTypeFactory.create(zaaktype__concept=True)
        StatusTypeFactory.create(zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")

        response = self.client.get(statustype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_statustype_status_concept(self):
        statustype1 = StatusTypeFactory.create(zaaktype__concept=True)
        StatusTypeFactory.create(zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")
        statustype1_url = reverse(
            "statustype-detail", kwargs={"uuid": statustype1.uuid}
        )

        response = self.client.get(statustype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{statustype1_url}")

    def test_filter_statustype_status_definitief(self):
        StatusTypeFactory.create(zaaktype__concept=True)
        statustype2 = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")
        statustype2_url = reverse(
            "statustype-detail", kwargs={"uuid": statustype2.uuid}
        )

        response = self.client.get(statustype_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{statustype2_url}")

    def test_validate_unknown_query_params(self):
        StatusTypeFactory.create_batch(2)
        url = reverse(StatusType)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class StatusTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        StatusTypeFactory.create_batch(2, zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")

        response = self.client.get(statustype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        StatusTypeFactory.create_batch(2, zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")

        response = self.client.get(statustype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
