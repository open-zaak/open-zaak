# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.db import IntegrityError, transaction
from django.test import TestCase

from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from ...models import BesluitTypeInformatieObjectType
from ..factories import BesluitTypeFactory, InformatieObjectTypeFactory
from ..factories.relatieklassen import BesluitTypeInformatieObjectTypeFactory

EXTERNAL_API_ROOT = "https://external.catalogi.nl/api/v1/"


class BesluitTypeInformatieObjectTypeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = ServiceFactory.create(
            api_type=APITypes.ztc, api_root=EXTERNAL_API_ROOT
        )

    def test_local_informatieobjecttype(self):
        besluittype = BesluitTypeFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create()

        relation = BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=informatieobjecttype
        )

        relation.refresh_from_db()
        self.assertEqual(relation._informatieobjecttype, informatieobjecttype)
        self.assertIsNone(relation._iotype_url)
        self.assertEqual(relation.informatieobjecttype, informatieobjecttype)

    def test_external_informatieobjecttype(self):
        besluittype = BesluitTypeFactory.create()
        url = f"{EXTERNAL_API_ROOT}informatieobjecttypen/2b2d2cb3-2a67-4b8e-a05f-cbbb7a0b3ff1"

        relation = BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=url
        )

        relation.refresh_from_db()
        self.assertIsNone(relation._informatieobjecttype)
        self.assertEqual(relation._iotype_url, url)
        self.assertEqual(relation._iotype_base_url, self.service)
        self.assertEqual(
            relation._iotype_relative_url,
            "informatieobjecttypen/2b2d2cb3-2a67-4b8e-a05f-cbbb7a0b3ff1",
        )

    def test_informatieobjecttype_is_required(self):
        besluittype = BesluitTypeFactory.create()

        with self.assertRaises(IntegrityError), transaction.atomic():
            BesluitTypeInformatieObjectType.objects.create(besluittype=besluittype)

    def test_local_and_external_informatieobjecttype_is_not_allowed(self):
        besluittype = BesluitTypeFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create()

        with self.assertRaises(IntegrityError), transaction.atomic():
            BesluitTypeInformatieObjectType.objects.create(
                besluittype=besluittype,
                _informatieobjecttype=informatieobjecttype,
                _iotype_url=f"{EXTERNAL_API_ROOT}informatieobjecttypen/1",
            )

    def test_local_informatieobjecttype_unique_per_besluittype(self):
        relation = BesluitTypeInformatieObjectTypeFactory.create()

        with self.assertRaises(IntegrityError), transaction.atomic():
            BesluitTypeInformatieObjectType.objects.create(
                besluittype=relation.besluittype,
                informatieobjecttype=relation.informatieobjecttype,
            )

        BesluitTypeInformatieObjectType.objects.create(
            besluittype=BesluitTypeFactory.create(),
            informatieobjecttype=relation.informatieobjecttype,
        )

    def test_external_informatieobjecttype_unique_per_besluittype(self):
        besluittype = BesluitTypeFactory.create()
        url = f"{EXTERNAL_API_ROOT}informatieobjecttypen/2b2d2cb3-2a67-4b8e-a05f-cbbb7a0b3ff1"
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=besluittype, informatieobjecttype=url
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            BesluitTypeInformatieObjectType.objects.create(
                besluittype=besluittype, informatieobjecttype=url
            )

        BesluitTypeInformatieObjectType.objects.create(
            besluittype=BesluitTypeFactory.create(), informatieobjecttype=url
        )
