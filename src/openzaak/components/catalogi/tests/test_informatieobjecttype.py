from unittest import skip

from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from ..models import InformatieObjectType
from .base import APITestCase
from .factories import (
    InformatieObjectTypeFactory,
    ZaakInformatieobjectTypeFactory,
    ZaakTypeFactory,
)
from .utils import get_operation_url


class InformatieObjectTypeAPITests(APITestCase):
    maxDiff = None

    def test_get_list_default_definitief(self):
        informatieobjecttype1 = InformatieObjectTypeFactory.create(concept=True)
        informatieobjecttype2 = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")
        informatieobjecttype2_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype2.uuid
        )

        response = self.client.get(informatieobjecttype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"], f"http://testserver{informatieobjecttype2_url}"
        )

    def test_get_detail(self):
        """Retrieve the details of a single `InformatieObjectType` object."""

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            zaaktypes=None,
            datum_begin_geldigheid="2019-01-01",
        )
        informatieobjecttype_detail_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype.uuid
        )

        response = self.client.get(informatieobjecttype_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            # 'categorie': 'informatieobjectcategorie',
            # 'einddatumObject': None,
            # 'ingangsdatumObject': '2018-01-01',
            # 'isVastleggingVoor': [],
            "catalogus": "http://testserver{}".format(self.catalogus_detail_url),
            # 'model': ['http://www.example.com'],
            "omschrijving": informatieobjecttype.omschrijving,
            # 'omschrijvingGeneriek': '',
            # 'toelichting': None,
            # 'trefwoord': ['abc', 'def'],
            "url": "http://testserver{}".format(informatieobjecttype_detail_url),
            "vertrouwelijkheidaanduiding": "",
            # 'isRelevantVoor': [],
            "beginGeldigheid": "2019-01-01",
            "eindeGeldigheid": None,
            "concept": True,
        }
        self.assertEqual(expected, response.json())

    @skip("Not MVP yet")
    def test_is_relevant_voor(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            zaaktypes=None,
            model=["http://www.example.com"],
            trefwoord=["abc", "def"],
        )
        informatieobjecttype_detail_url = get_operation_url(
            "informatieobjecttype_read",
            catalogus_uuid=self.catalogus.uuid,
            uuid=informatieobjecttype.uuid,
        )

        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)

        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype,
            informatieobjecttype=informatieobjecttype,
            volgnummer=1,
            richting="richting",
        )

        response = self.client.get(informatieobjecttype_detail_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("isRelevantVoor" in data)
        self.assertEqual(len(data["isRelevantVoor"]), 1)
        self.assertEqual(
            data["isRelevantVoor"][0],
            "http://testserver{}".format(
                reverse("zktiot-detail", args=[zaaktype.pk, ziot.pk])
            ),
        )

    @skip("Not MVP yet")
    def test_is_vastlegging_voor(self):
        pass

    def test_create_informatieobjecttype(self):
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
        }
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        informatieobjecttype = InformatieObjectType.objects.get()

        self.assertEqual(informatieobjecttype.omschrijving, "test")
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertEqual(informatieobjecttype.concept, True)

    def test_publish_informatieobjecttype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttypee_url = get_operation_url(
            "informatieobjecttype_publish", uuid=informatieobjecttype.uuid
        )

        response = self.client.post(informatieobjecttypee_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        informatieobjecttype.refresh_from_db()

        self.assertEqual(informatieobjecttype.concept, False)

    def test_delete_informatieobjecttype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttypee_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype.uuid
        )

        response = self.client.delete(informatieobjecttypee_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            InformatieObjectType.objects.filter(id=informatieobjecttype.id)
        )

    def test_delete_informatieobjecttype_fail_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttypee_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype.uuid
        )

        response = self.client.delete(informatieobjecttypee_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["detail"], "Alleen concepten kunnen worden verwijderd.")


class InformatieObjectTypeFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_informatieobjecttype_status_alles(self):
        InformatieObjectTypeFactory.create(concept=True)
        InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.get(informatieobjecttype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_informatieobjecttype_status_concept(self):
        informatieobjecttype1 = InformatieObjectTypeFactory.create(concept=True)
        informatieobjecttype2 = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")
        informatieobjecttype1_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype1.uuid
        )

        response = self.client.get(informatieobjecttype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"], f"http://testserver{informatieobjecttype1_url}"
        )

    def test_filter_informatieobjecttype_status_definitief(self):
        informatieobjecttype1 = InformatieObjectTypeFactory.create(concept=True)
        informatieobjecttype2 = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")
        informatieobjecttype2_url = get_operation_url(
            "informatieobjecttype_read", uuid=informatieobjecttype2.uuid
        )

        response = self.client.get(
            informatieobjecttype_list_url, {"status": "definitief"}
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["url"], f"http://testserver{informatieobjecttype2_url}"
        )

    def test_validate_unknown_query_params(self):
        InformatieObjectTypeFactory.create_batch(2)
        url = reverse(InformatieObjectType)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class InformatieObjectTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        InformatieObjectTypeFactory.create_batch(2, concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.get(informatieobjecttype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        InformatieObjectTypeFactory.create_batch(2, concept=False)
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.get(informatieobjecttype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])
