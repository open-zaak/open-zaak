from django.test import override_settings

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import serialise_eio
from openzaak.utils.tests import APICMISTestCase

from ..factories import ZaakInformatieObjectFactory


@override_settings(CMIS_ENABLED=True)
class UniqueRepresentationCMISTestCase(APICMISTestCase):
    def test_zaakinformatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        eio_url = eio.get_url()
        self.adapter.register_uri("GET", eio_url, json=serialise_eio(eio, eio_url))
        zio = ZaakInformatieObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            informatieobject=eio_url,
        )

        self.assertEqual(
            zio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
