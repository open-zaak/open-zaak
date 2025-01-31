# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import override_settings
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

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

        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            zaaktypen=None,
            datum_begin_geldigheid="2019-01-01",
            trefwoord=["abc", "def"],
        )
        informatieobjecttype_detail_url = get_operation_url(
            "informatieobjecttype_read", uuid=iotype.uuid
        )

        response = self.client.get(informatieobjecttype_detail_url)

        self.assertEqual(response.status_code, 200)

        expected = {
            "catalogus": "http://testserver{}".format(self.catalogus_detail_url),
            "omschrijving": iotype.omschrijving,
            "url": "http://testserver{}".format(informatieobjecttype_detail_url),
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
            "eindeGeldigheid": None,
            "concept": True,
            "trefwoord": ["abc", "def"],
            "besluittypen": [],
            "omschrijvingGeneriek": {
                "informatieobjecttypeOmschrijvingGeneriek": iotype.omschrijving_generiek_informatieobjecttype,
                "definitieInformatieobjecttypeOmschrijvingGeneriek": iotype.omschrijving_generiek_definitie,
                "herkomstInformatieobjecttypeOmschrijvingGeneriek": iotype.omschrijving_generiek_herkomst,
                "hierarchieInformatieobjecttypeOmschrijvingGeneriek": iotype.omschrijving_generiek_hierarchie,
                "opmerkingInformatieobjecttypeOmschrijvingGeneriek": iotype.omschrijving_generiek_opmerking,
            },
            "informatieobjectcategorie": iotype.informatieobjectcategorie,
            "zaaktypen": [],
            "beginObject": "2019-01-01",
            "eindeObject": None,
        }
        self.assertEqual(expected, response.json())

    def test_create_informatieobjecttype(self):
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        informatieobjecttype = InformatieObjectType.objects.get()

        self.assertEqual(informatieobjecttype.omschrijving, "test")
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertEqual(informatieobjecttype.concept, True)
        self.assertEqual(informatieobjecttype.informatieobjectcategorie, "main")

    def test_create_informatieobjecttype_with_same_omschrijving(self):
        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2019-01-01",
        )

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-02",
            "informatieobjectcategorie": "main",
        }
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        informatieobjecttype = InformatieObjectType.objects.get(
            datum_begin_geldigheid="2019-01-02"
        )

        self.assertEqual(informatieobjecttype.omschrijving, "test")
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertEqual(informatieobjecttype.concept, True)

    def test_create_informatieobjecttype_succeeds_with_same_omschrijving_and_overlapping_dates(
        self,
    ):
        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2019-01-03",
        )

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-02",
            "informatieobjectcategorie": "main",
        }
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_informatieobject_type_with_omschrijving_generiek(self):
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "informatieobjectcategorie": "main",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "omschrijvingGeneriek": {
                "informatieobjecttypeOmschrijvingGeneriek": "some iotype",
                "definitieInformatieobjecttypeOmschrijvingGeneriek": "detailed description",
                "herkomstInformatieobjecttypeOmschrijvingGeneriek": "test",
                "hierarchieInformatieobjecttypeOmschrijvingGeneriek": "high",
                "opmerkingInformatieobjecttypeOmschrijvingGeneriek": "comment",
            },
        }
        informatieobjecttype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        informatieobjecttype = InformatieObjectType.objects.get()

        self.assertEqual(informatieobjecttype.omschrijving, "test")
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertEqual(informatieobjecttype.concept, True)
        self.assertEqual(
            informatieobjecttype.omschrijving_generiek_informatieobjecttype,
            "some iotype",
        )
        self.assertEqual(
            informatieobjecttype.omschrijving_generiek_definitie, "detailed description"
        )
        self.assertEqual(informatieobjecttype.omschrijving_generiek_herkomst, "test")
        self.assertEqual(informatieobjecttype.omschrijving_generiek_hierarchie, "high")
        self.assertEqual(
            informatieobjecttype.omschrijving_generiek_opmerking, "comment"
        )
        self.assertEqual(informatieobjecttype.informatieobjectcategorie, "main")

    def test_publish_informatieobjecttype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttypee_url = get_operation_url(
            "informatieobjecttype_publish", uuid=informatieobjecttype.uuid
        )

        response = self.client.post(informatieobjecttypee_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        informatieobjecttype.refresh_from_db()

        self.assertEqual(informatieobjecttype.concept, False)

    def test_publish_informatieobjecttype_with_overlapping_informatieobjecttype(self):

        catalogus = CatalogusFactory.create()
        old_informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            concept=False,
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-10-10",
            concept=True,
        )
        informatieobjecttypee_url = get_operation_url(
            "informatieobjecttype_publish", uuid=informatieobjecttype.uuid
        )

        response = self.client.post(informatieobjecttypee_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.concept, True)

        error = get_validation_errors(response, "beginGeldigheid")
        self.assertEqual(error["code"], "overlap")
        self.assertEqual(
            error["reason"],
            _(
                "Dit {} komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
            ).format(InformatieObjectType._meta.verbose_name),
        )

        old_informatieobjecttype.datum_einde_geldigheid = "2018-01-09"
        old_informatieobjecttype.save()

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
            "informatieobjectcategorie": "main",
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
            "informatieobjectcategorie": "main",
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
            "informatieobjectcategorie": "main",
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
            "informatieobjectcategorie": "main",
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
            "informatieobjectcategorie": "main",
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
            "informatieobjectcategorie": "main",
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
    url = reverse_lazy("informatieobjecttype-list")

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

    def test_filter_omschrijving(self):
        iotype = InformatieObjectTypeFactory.create(omschrijving="some", concept=False)
        InformatieObjectTypeFactory.create(omschrijving="other", concept=False)

        response = self.client.get(self.url, {"omschrijving": "some"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(iotype)}")

    def test_filter_geldigheid(self):
        iotype = InformatieObjectTypeFactory.create(
            datum_begin_geldigheid=date(2020, 1, 1),
            datum_einde_geldigheid=date(2020, 2, 1),
            concept=False,
        )
        InformatieObjectTypeFactory.create(
            datum_begin_geldigheid=date(2020, 2, 1), concept=False
        )

        response = self.client.get(self.url, {"datumGeldigheid": "2020-01-10"})

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(iotype)}")

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        iotype = InformatieObjectTypeFactory.create(omschrijving="some", concept=False)
        InformatieObjectTypeFactory.create(omschrijving="other", concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=iotype
        )
        ZaakTypeInformatieObjectTypeFactory(informatieobjecttype=iotype)
        zaaktype_url = f"http://openzaak.nl{reverse(zaaktype)}"

        response = self.client.get(
            self.url, {"zaaktype": zaaktype_url}, headers={"host": "openzaak.nl"}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://openzaak.nl{reverse(iotype)}")

    @override_settings(ALLOWED_HOSTS=["openzaak.nl"])
    def test_filter_zaaktype_not_exist(self):
        InformatieObjectTypeFactory.create(omschrijving="some", concept=False)
        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": "221e7626-a556-4eb5-9714-e7693f82c2dd"}
        )

        response = self.client.get(
            self.url,
            {"zaaktype": f"http://openzaak.nl{zaaktype_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)


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

    def test_pagination_pagesize_param(self):
        InformatieObjectTypeFactory.create_batch(10, concept=False)
        iotype_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.get(iotype_list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{iotype_list_url}?page=2&pageSize=5"
        )
