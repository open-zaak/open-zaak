# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ZaakTypeConceptValidator
from ..models import CheckListItem, StatusType
from .base import APITestCase
from .factories import (
    CheckListItemFactory,
    EigenschapFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakObjectTypeFactory,
    ZaakTypeFactory,
)
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
            toelichting="description",
        )
        eigenschap = EigenschapFactory.create(
            zaaktype=statustype.zaaktype, statustype=statustype
        )
        zaakobjecttype = ZaakObjectTypeFactory.create(
            zaaktype=statustype.zaaktype, statustype=statustype
        )
        statustype_detail_url = reverse(
            "statustype-detail", kwargs={"uuid": statustype.uuid}
        )
        checklistitem = CheckListItemFactory.create(statustype=statustype)
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
            "zaaktypeIdentificatie": zaaktype.identificatie,
            "volgnummer": statustype.statustypevolgnummer,
            "isEindstatus": True,
            "informeren": False,
            "catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
            "doorlooptijd": None,
            "toelichting": "description",
            "checklistitemStatustype": [
                {
                    "itemnaam": checklistitem.itemnaam,
                    "toelichting": checklistitem.toelichting,
                    "verplicht": checklistitem.verplicht,
                    "vraagstelling": checklistitem.vraagstelling,
                }
            ],
            "eigenschappen": [f"http://testserver{reverse(eigenschap)}"],
            "zaakobjecttypen": [f"http://testserver{reverse(zaakobjecttype)}"],
            "beginGeldigheid": None,
            "eindeGeldigheid": None,
            "beginObject": None,
            "eindeObject": None,
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
            "beginGeldigheid": "2023-01-01",
            "eindeGeldigheid": "2023-12-01",
        }
        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        statustype = StatusType.objects.get()

        self.assertEqual(statustype.statustype_omschrijving, "Besluit genomen")
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(statustype.datum_begin_geldigheid, date(2023, 1, 1))
        self.assertEqual(statustype.datum_einde_geldigheid, date(2023, 12, 1))

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

    def test_create_statustype_with_checklist(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        statustype_list_url = reverse("statustype-list")
        data = {
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
            "checklistitemStatustype": [
                {
                    "itemnaam": "item 1",
                    "toelichting": "description",
                    "verplicht": True,
                    "vraagstelling": "some question",
                }
            ],
        }
        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        statustype = StatusType.objects.get()

        self.assertEqual(statustype.statustype_omschrijving, "Besluit genomen")
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(statustype.checklistitem_set.count(), 1)

        checklistitem = statustype.checklistitem_set.get()
        self.assertEqual(checklistitem.itemnaam, "item 1")
        self.assertEqual(checklistitem.toelichting, "description")
        self.assertTrue(checklistitem.verplicht)
        self.assertEqual(checklistitem.vraagstelling, "some question")

    def test_create_statustype_with_end_date_before_start_date(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        statustype_list_url = reverse("statustype-list")
        data = {
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": "http://testserver{}".format(zaaktype_url),
            "volgnummer": 2,
            "checklistitemStatustype": [
                {
                    "itemnaam": "item 1",
                    "toelichting": "description",
                    "verplicht": True,
                    "vraagstelling": "some question",
                }
            ],
            "beginGeldigheid": "2023-12-01",
            "eindeGeldigheid": "2023-01-01",
        }

        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "date-mismatch")

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

    def test_partial_update_statustype_checklist(self):
        zaaktype = ZaakTypeFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)
        old_checklistitem = CheckListItemFactory.create(
            statustype=statustype, itemnaam="old"
        )

        response = self.client.patch(
            statustype_url,
            {
                "checklistitemStatustype": [
                    {
                        "itemnaam": "new",
                        "toelichting": "description",
                        "verplicht": True,
                        "vraagstelling": "some question",
                    }
                ]
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        statustype.refresh_from_db()
        self.assertEqual(statustype.checklistitem_set.count(), 1)

        new_checklistitem = statustype.checklistitem_set.get()
        self.assertEqual(new_checklistitem.itemnaam, "new")
        self.assertNotEqual(old_checklistitem.id, new_checklistitem.id)
        self.assertFalse(CheckListItem.objects.filter(id=old_checklistitem.id).exists())


class StatusTypeFilterAPITests(APITestCase):
    maxDiff = None
    url = reverse_lazy("statustype-list")

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

    def test_filter_zaaktype_identificatie(self):
        statustype = StatusTypeFactory.create(
            zaaktype__identificatie="some", zaaktype__concept=False
        )
        StatusTypeFactory.create(
            zaaktype__identificatie="other", zaaktype__concept=False
        )

        response = self.client.get(self.url, {"zaaktypeIdentificatie": "some"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(statustype)}")

    def test_filter_geldigheid(self):
        statustype = StatusTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            zaaktype__concept=False,
        )
        StatusTypeFactory.create(
            datum_begin_geldigheid=date(2020, 2, 1), zaaktype__concept=False
        )

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(statustype)}")


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

    def test_pagination_pagesize_param(self):
        StatusTypeFactory.create_batch(10, zaaktype__concept=False)
        statustype_list_url = reverse("statustype-list")

        response = self.client.get(statustype_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{statustype_list_url}?page=2&pageSize=5"
        )
