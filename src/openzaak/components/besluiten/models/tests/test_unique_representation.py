from rest_framework.test import APITestCase

from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)

from .factories import BesluitFactory, BesluitInformatieObjectFactory


class UniqueRepresentationTestCase(APITestCase):
    def test_besluit(self):
        besluit = BesluitFactory(identificatie="5d940d52-ff5e-4b18-a769-977af9130c04")

        self.assertEqual(
            besluit.unique_representation(), "5d940d52-ff5e-4b18-a769-977af9130c04"
        )

    def test_besluitinformatieobject(self):
        io = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        bio = BesluitInformatieObjectFactory(
            besluit__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            informatieobject=io.canonical,
        )

        self.assertEqual(
            bio.unique_representation(),
            "(5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
