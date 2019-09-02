from django.test import override_settings, tag

from rest_framework.test import APITestCase
from zds_client.tests.mocks import mock_client

from .factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
)
from ..models import ObjectInformatieObject
from openzaak.components.zaken.models.tests.factories import ZaakFactory


class UniqueRepresentationTestCase(APITestCase):
    def test_eio(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )

        self.assertEqual(
            eio.unique_representation(),
            "730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04",
        )

    def test_gebruiksrechten(self):
        gebruiksrechten = GebruiksrechtenFactory(
            informatieobject__latest_version__bronorganisatie=730924658,
            informatieobject__latest_version__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            omschrijving_voorwaarden="some conditions",
        )

        self.assertEqual(
            gebruiksrechten.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some conditions",
        )

    @tag("oio")
    def test_oio(self):
        zaak = ZaakFactory.create(identificatie='12345')
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04"
        )
        oio = ObjectInformatieObject.objects.create(zaak=zaak, object_type='zaak', informatieobject=eio.canonical)

        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
