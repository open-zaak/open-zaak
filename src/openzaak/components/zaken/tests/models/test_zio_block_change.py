# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase

from openzaak.utils.query import QueryBlocked

from ...models import ZaakInformatieObject
from ..factories import ZaakInformatieObjectFactory


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zio = ZaakInformatieObjectFactory.create()

    def test_update(self):
        self.assertRaises(
            QueryBlocked, ZaakInformatieObject.objects.update, titel="new"
        )

    def test_delete(self):
        self.assertRaises(QueryBlocked, ZaakInformatieObject.objects.all().delete)

    def test_bulk_update(self):
        self.zio.title = "new"
        self.assertRaises(
            QueryBlocked,
            ZaakInformatieObject.objects.bulk_update,
            [self.zio],
            fields=["titel"],
        )

    def test_bulk_create(self):
        zio = ZaakInformatieObjectFactory.build()
        self.assertRaises(QueryBlocked, ZaakInformatieObject.objects.bulk_create, [zio])
