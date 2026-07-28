# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""

import uuid

from rest_framework import status
from rest_framework.test import APITestCase as _APITestCase
from vng_api_common.constants import (
    ComponentTypes,
)
from vng_api_common.tests import AuthCheckMixin

from openzaak.components.catalogi.api.scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
)
from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.base import APITestCase
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.utils.urls import reverse


class ReadTests(AuthCheckMixin, _APITestCase):
    def test_cannot_read_without_correct_scope(self):
        dummy_uuid = str(uuid.uuid4())
        urls = [
            reverse("catalogi:informatieobjecttype-list"),
            reverse(
                "catalogi:informatieobjecttype-detail", kwargs={"uuid": dummy_uuid}
            ),
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


class PublishedTypesForcedWriteTests(APITestCase):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_WRITE]
    component = ComponentTypes.ztc

    def test_update_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_partial_update_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "same"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "same")

    def test_update_informatieobjecttype_related_to_non_concept_resources(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus
        )
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        BesluitTypeFactory.create(
            concept=False,
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_partial_update_informatieobjecttype_related_to_non_concept_resources(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus
        )
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        BesluitTypeFactory.create(
            concept=False,
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "test"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")
