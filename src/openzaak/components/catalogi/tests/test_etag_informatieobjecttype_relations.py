# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.tests.utils.auth import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import BesluitTypeInformatieObjectType
from .factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)

EXTERNAL_IOTYPE = (
    "https://external.documenten.nl/api/v1/informatieobjecttypen/"
    "2b2d2cb3-2a67-4b8e-a05f-cbbb7a0b3ff1"
)


class InformatieObjectTypeRelationETagTests(JWTAuthMixin, APITransactionTestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        super().setUpTestData()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root="https://external.documenten.nl/api/v1/",
            auth_type=AuthTypes.no_auth,
        )

    def get_etag(self, obj, namespace: str) -> str:
        response = self.client.get(reverse(obj, namespace=namespace))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return response.headers["ETag"]

    def test_besluittype_relation_created(self):
        besluittype = BesluitTypeFactory.create(informatieobjecttypen=[])
        iotype = InformatieObjectTypeFactory.create(
            zaaktypen=[], catalogus=besluittype.catalogus
        )
        besluittype_etag = self.get_etag(besluittype, "zaken")
        iotype_etag = self.get_etag(iotype, "documenten")

        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=iotype
        )

        self.assertNotEqual(self.get_etag(besluittype, "zaken"), besluittype_etag)
        self.assertNotEqual(self.get_etag(iotype, "documenten"), iotype_etag)

    def test_besluittype_relation_deleted(self):
        besluittype = BesluitTypeFactory.create(informatieobjecttypen=[])
        iotype = InformatieObjectTypeFactory.create(
            zaaktypen=[], catalogus=besluittype.catalogus
        )
        relation = BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=iotype
        )
        besluittype_etag = self.get_etag(besluittype, "zaken")
        iotype_etag = self.get_etag(iotype, "documenten")

        relation.delete()

        self.assertNotEqual(self.get_etag(besluittype, "zaken"), besluittype_etag)
        self.assertNotEqual(self.get_etag(iotype, "documenten"), iotype_etag)

    def test_besluittype_relation_replaced_via_api(self):
        besluittype = BesluitTypeFactory.create(informatieobjecttypen=[])
        iotype = InformatieObjectTypeFactory.create(
            zaaktypen=[], catalogus=besluittype.catalogus
        )
        iotype_etag = self.get_etag(iotype, "documenten")
        response = self.client.get(reverse(besluittype, namespace="zaken"))
        data = response.json()
        data["informatieobjecttypen"] = [
            f"http://testserver{reverse(iotype, namespace='documenten')}"
        ]

        response = self.client.put(reverse(besluittype, namespace="zaken"), data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertNotEqual(self.get_etag(iotype, "documenten"), iotype_etag)

    def test_delete_besluittype_with_relations(self):
        besluittype = BesluitTypeFactory.create(informatieobjecttypen=[])
        iotype = InformatieObjectTypeFactory.create(
            zaaktypen=[], catalogus=besluittype.catalogus
        )
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=iotype
        )
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=EXTERNAL_IOTYPE
        )

        besluittype.delete()

        self.assertFalse(BesluitTypeInformatieObjectType.objects.exists())
