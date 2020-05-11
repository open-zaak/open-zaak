from django.test import TestCase, override_settings

from openzaak.components.besluiten.tests.utils import serialise_eio
from openzaak.components.documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from openzaak.utils.query import QueryBlocked
from openzaak.utils.tests import APICMISTestCase

from ...models import ZaakInformatieObject
from ..factories import ZaakInformatieObjectFactory


@override_settings(CMIS_ENABLED=False)
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


@override_settings(CMIS_ENABLED=True)
class BlockChangeCMISTestCase(APICMISTestCase):

    def setUp(self) -> None:
        super().setUp()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.register_uri('GET', eio_url, json=serialise_eio(eio, eio_url))
        self.zio = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url
        )

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
