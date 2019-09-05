from django.test import TestCase

from ...models import ZaakInformatieObject
from .factories import ZaakInformatieObjectFactory


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zio = ZaakInformatieObjectFactory.create()

    def test_update(self):
        self.assertRaises(TypeError, ZaakInformatieObject.objects.update, titel="new")

    def test_delete(self):
        self.assertRaises(TypeError, ZaakInformatieObject.objects.delete)

    def test_bulk_update(self):
        self.zio.title = "new"
        self.assertRaises(
            TypeError,
            ZaakInformatieObject.objects.bulk_update,
            [self.zio],
            fields=["titel"],
        )

    def test_bulk_create(self):
        zio = ZaakInformatieObjectFactory.build()
        self.assertRaises(TypeError, ZaakInformatieObject.objects.bulk_create, [zio])
