from django.test import TestCase

from vng_api_common.constants import RelatieAarden

from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)

from ...models import BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory


class BlockChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bio = BesluitInformatieObjectFactory.create()

    def test_update(self):
        self.assertRaises(
            TypeError,
            BesluitInformatieObject.objects.update,
            aard_relatie=RelatieAarden.hoort_bij,
        )

    def test_delete(self):
        self.assertRaises(TypeError, BesluitInformatieObject.objects.delete)

    def test_bulk_update(self):
        self.bio.aard_relatie = RelatieAarden.hoort_bij
        self.assertRaises(
            TypeError,
            BesluitInformatieObject.objects.bulk_update,
            [self.bio],
            fields=["aard_relatie"],
        )

    def test_bulk_create(self):
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        bio = BesluitInformatieObject(
            besluit=besluit,
            informatieobject=eio.canonical,
            aard_relatie=RelatieAarden.hoort_bij,
        )
        self.assertRaises(TypeError, BesluitInformatieObject.objects.bulk_create, [bio])
