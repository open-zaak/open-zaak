# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.query import QueryBlocked

from ...models import BesluitInformatieObject
from ..factories import BesluitFactory, BesluitInformatieObjectFactory


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bio = BesluitInformatieObjectFactory.create()

    def test_update(self):
        self.assertRaises(
            QueryBlocked, BesluitInformatieObject.objects.update, uuid=uuid.uuid4()
        )

    def test_delete(self):
        self.assertRaises(QueryBlocked, BesluitInformatieObject.objects.all().delete)

    def test_bulk_update(self):
        self.bio.uuid = uuid.uuid4()
        self.assertRaises(
            QueryBlocked,
            BesluitInformatieObject.objects.bulk_update,
            [self.bio],
            fields=["uuid"],
        )

    def test_bulk_create(self):
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        bio = BesluitInformatieObject(
            besluit=besluit, informatieobject=eio.canonical, uuid=uuid.uuid4()
        )
        self.assertRaises(
            QueryBlocked, BesluitInformatieObject.objects.bulk_create, [bio]
        )
