# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest import skip

from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from ..api.scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..api.validators import ConceptUpdateValidator, M2MConceptUpdateValidator
from ..models import InformatieObjectType
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from .utils import get_operation_url


class InformatieObjectTypeAPITests(APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE]
    component = ComponentTypes.ztc

    def test_get_list_default_definitief(self):
        InformatieObjectTypeFactory.create(concept=True)
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
            zaaktypen=None,
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
            zaaktypen=None,
            model=["http://www.example.com"],
            trefwoord=["abc", "def"],
        )
        informatieobjecttype_detail_url = get_operation_url(
            "informatieobjecttype_read",
            catalogus_uuid=self.catalogus.uuid,
            uuid=informatieobjecttype.uuid,
        )

        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)

        ziot = ZaakTypeInformatieObjectTypeFactory.create(
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

    def test_create_informatieobjecttype_fail_not_unique(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        list_url = get_operation_url("informatieobjecttype_list")
        data = {
            "catalogus": f"http://testserver{reverse(informatieobjecttype.catalogus)}",
            "omschrijving": informatieobjecttype.omschrijving,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.post(list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-object")

    def test_update_informatieobjecttype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "test")

        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_update_informatieobjecttype_fail_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ConceptUpdateValidator.code)

    def test_partial_update_informatieobjecttype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "ja"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "ja")

        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "ja")

    def test_partial_update_informatieobjecttype_fail_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "same"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], ConceptUpdateValidator.code)

    def test_delete_informatieobjecttype_not_related_to_non_concept_zaaktype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        zaaktype = ZaakTypeFactory.create()
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_delete_informatieobjecttype_not_related_to_non_concept_besluittype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        BesluitTypeFactory.create(informatieobjecttypen=[informatieobjecttype])

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_delete_informatieobjecttype_related_to_non_concept_zaaktype_fails(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_delete_informatieobjecttype_related_to_non_concept_besluittype_fails(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype], concept=False
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_update_informatieobjecttype_not_related_to_non_concept_zaaktype(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "test")
        informatieobjecttype.delete()

    def test_update_informatieobjecttype_not_related_to_non_concept_besluittype(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype], catalogus=catalogus
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "test")
        informatieobjecttype.delete()

    def test_update_informatieobjecttype_related_to_non_concept_zaaktype_fails(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        informatieobjecttype.delete()

    def test_update_informatieobjecttype_related_to_non_concept_besluittype_fails(self):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)

        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype],
            concept=False,
            catalogus=catalogus,
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        informatieobjecttype.delete()

    def test_partial_update_informatieobjecttype_not_related_to_non_concept_zaaktype(
        self,
    ):
        catalogus = CatalogusFactory.create()

        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "test"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "test")
        informatieobjecttype.delete()

    def test_partial_update_informatieobjecttype_not_related_to_non_concept_besluittype(
        self,
    ):
        catalogus = CatalogusFactory.create()

        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype], catalogus=catalogus
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "test"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "test")
        informatieobjecttype.delete()

    def test_partial_update_informatieobjecttype_related_to_non_concept_zaaktype_fails(
        self,
    ):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus, concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            informatieobjecttype_url, {"omschrijving": "aangepast"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        informatieobjecttype.delete()

    def test_partial_update_informatieobjecttype_related_to_non_concept_besluittype_fails(
        self,
    ):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype],
            catalogus=catalogus,
            concept=False,
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            informatieobjecttype_url, {"omschrijving": "aangepast"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], M2MConceptUpdateValidator.code)
        informatieobjecttype.delete()

    def test_partial_update_non_concept_informatieobjecttype_einde_geldigheid(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            informatieobjecttype_url, {"eindeGeldigheid": "2020-01-01"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")

    def test_partial_update_informatieobjecttype_einde_geldigheid_related_to_non_concept_zaaktype(
        self,
    ):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus, concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            informatieobjecttype_url, {"eindeGeldigheid": "2020-01-01"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")
        informatieobjecttype.delete()

    def test_partial_update_informatieobjecttype_einde_geldigheid_related_to_non_concept_besluittype(
        self,
    ):
        catalogus = CatalogusFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(catalogus=catalogus)
        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype],
            catalogus=catalogus,
            concept=False,
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            informatieobjecttype_url, {"eindeGeldigheid": "2020-01-01"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["einde_geldigheid"], "2020-01-01")
        informatieobjecttype.delete()


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
        InformatieObjectTypeFactory.create(concept=False)
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
        InformatieObjectTypeFactory.create(concept=True)
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
