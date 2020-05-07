from rest_framework.test import APITestCase

from django.conf import settings
from django.test import override_settings

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase

from ...tests.factories import BesluitFactory, BesluitInformatieObjectFactory
from ..utils import serialise_eio


@override_settings(CMIS_ENABLED=False)
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


@override_settings(CMIS_ENABLED=True)
class UniqueRepresentationTestCMISCase(APICMISTestCase):
    def test_besluit(self):
        besluit = BesluitFactory(identificatie="5d940d52-ff5e-4b18-a769-977af9130c04")

        self.assertEqual(
            besluit.unique_representation(), "5d940d52-ff5e-4b18-a769-977af9130c04"
        )

    def test_besluitinformatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        eio_url = eio.get_url()
        self.adapter.register_uri('GET', eio_url, json=serialise_eio(eio, eio_url))

        bio = BesluitInformatieObjectFactory(
            besluit__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            informatieobject=eio_url,
        )

        self.assertEqual(
            bio.unique_representation(),
            "(5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
