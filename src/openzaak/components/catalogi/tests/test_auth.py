# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
import uuid

from rest_framework import status
from rest_framework.test import APITestCase as _APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import AuthCheckMixin, reverse

from ..api.scopes import SCOPE_CATALOGI_FORCED_DELETE
from ..models import (
    BesluitType,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


class ReadTests(AuthCheckMixin, _APITestCase):
    def test_cannot_read_without_correct_scope(self):
        dummy_uuid = str(uuid.uuid4())
        urls = [
            # root
            reverse("catalogus-list"),
            reverse("catalogus-detail", kwargs={"uuid": dummy_uuid}),
            # nested one level
            reverse("zaaktype-list"),
            reverse("zaaktype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("informatieobjecttype-list"),
            reverse("informatieobjecttype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("besluittype-list"),
            reverse("besluittype-detail", kwargs={"uuid": dummy_uuid}),
            # nested two levels
            reverse("statustype-list"),
            reverse("statustype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("eigenschap-list"),
            reverse("eigenschap-detail", kwargs={"uuid": dummy_uuid}),
            reverse("roltype-list"),
            reverse("roltype-detail", kwargs={"uuid": dummy_uuid}),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


class PublishedTypesForcedDeletionTests(APITestCase):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_DELETE]
    component = ComponentTypes.ztc

    def test_force_delete_besluittype_not_concept(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        response = self.client.delete(besluittype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BesluitType.objects.exists())

    def test_force_delete_besluittype_related_to_non_concept_resource(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        for resource in ["zaaktypen", "informatieobjecttypen"]:
            with self.subTest(resource=resource):
                related = zaaktype if resource == "zaaktypen" else informatieobjecttype
                besluittype = BesluitTypeFactory.create(**{resource: [related]})
                besluittype_url = reverse(besluittype)

                response = self.client.delete(besluittype_url)

                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(BesluitType.objects.exists())

    def test_force_delete_eigenschap_not_concept_zaaktype(self):
        eigenschap = EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_url = reverse(eigenschap)

        response = self.client.delete(eigenschap_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Eigenschap.objects.exists())

    def test_force_delete_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_informatieobjecttype_related_to_non_concept_zaaktype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_informatieobjecttype_related_to_non_concept_besluittype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype], concept=False
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_ziot_not_concept_zaaktype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(zaaktype__concept=False)
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_force_delete_ziot_not_concept_informatieobjecttype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_force_delete_resultaattype_not_concept_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_url = reverse(resultaattype)

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResultaatType.objects.exists())

    def test_force_delete_roltype_not_concept_zaaktype(self):
        roltype = RolTypeFactory.create(zaaktype__concept=False)
        roltype_url = reverse(roltype)

        response = self.client.delete(roltype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RolType.objects.exists())

    def test_force_delete_statustype_not_concept_zaaktype(self):
        statustype = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_url = reverse(statustype)

        response = self.client.delete(statustype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StatusType.objects.exists())

    def test_delete_zaaktype_fail_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())

    def test_force_delete_zaaktype_related_to_non_concept_besluittype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(
            catalogus=catalogus, zaaktypen=[zaaktype], concept=False
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())

    def test_force_delete_zaaktype_related_to_non_concept_informatieobjecttype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False, zaaktypen=[]
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())
