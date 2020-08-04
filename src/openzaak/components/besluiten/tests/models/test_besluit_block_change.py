# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.utils.query import QueryBlocked

from ...models import Besluit
from ..factories import BesluitFactory


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.besluit = BesluitFactory.create()

    def test_update(self):
        self.assertRaises(QueryBlocked, Besluit.objects.update, uuid=uuid.uuid4())

    def test_delete(self):
        self.assertRaises(QueryBlocked, Besluit.objects.all().delete)

    def test_bulk_update(self):
        self.besluit.uuid = uuid.uuid4()
        self.assertRaises(
            QueryBlocked, Besluit.objects.bulk_update, [self.besluit], fields=["uuid"],
        )

    def test_bulk_create(self):
        besluittype = BesluitTypeFactory.create()
        besluit = BesluitFactory.build(besluittype=besluittype)

        self.assertRaises(QueryBlocked, Besluit.objects.bulk_create, [besluit])
