# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import IntegrityError
from django.test import TestCase, tag

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.utils.query import QueryBlocked

from ...models import ObjectInformatieObject
from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


@tag("oio")
class OIOTests(TestCase):
    def test_not_both_zaak_besluit(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create()

        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(
                informatieobject=canonical, zaak=zaak, besluit=besluit
            )

    def test_either_zaak_or_besluit_required(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()

        with self.assertRaises(IntegrityError):
            ObjectInformatieObject.objects.create(
                informatieobject=canonical, zaak=None, besluit=None
            )

    def test_zio_creates_oio(self):
        zio = ZaakInformatieObjectFactory.create()

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(oio.informatieobject, zio.informatieobject)
        self.assertEqual(oio.object, zio.zaak)

    def test_bio_creates_oio(self):
        bio = BesluitInformatieObjectFactory.create()

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(oio.informatieobject, bio.informatieobject)
        self.assertEqual(oio.object, bio.besluit)

    def test_zio_delete_oio(self):
        zio = ZaakInformatieObjectFactory.create()

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        zio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)

    def test_bio_delete_oio(self):
        bio = BesluitInformatieObjectFactory.create()

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)

        bio.delete()

        self.assertEqual(ObjectInformatieObject.objects.count(), 0)


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ZaakInformatieObjectFactory.create()
        cls.oio = ObjectInformatieObject.objects.get()

    def test_update(self):
        self.assertRaises(
            QueryBlocked, ObjectInformatieObject.objects.update, object_type="besluit"
        )

    def test_delete(self):
        self.assertRaises(QueryBlocked, ObjectInformatieObject.objects.all().delete)

    def test_bulk_update(self):
        self.oio.object_type = "besluit"
        self.assertRaises(
            QueryBlocked,
            ObjectInformatieObject.objects.bulk_update,
            [self.oio],
            fields=["object_type"],
        )

    def test_bulk_create(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()
        zaak = ZaakFactory.create()
        oio = ObjectInformatieObject(
            informatieobject=canonical, zaak=zaak, object_type="zaak"
        )

        self.assertRaises(
            QueryBlocked, ObjectInformatieObject.objects.bulk_create, [oio]
        )
