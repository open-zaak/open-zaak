from django.test import override_settings

from rest_framework.test import APITestCase
from zds_client.tests.mocks import mock_client

from .factories import (
    EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory,
    ObjectInformatieObjectFactory
)


@override_settings(
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class UniqueRepresentationTestCase(APITestCase):

    def test_eio(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie='5d940d52-ff5e-4b18-a769-977af9130c04'
        )

        self.assertEqual(
            eio.unique_representation(),
            '730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04'
        )

    def test_gebruiksrechten(self):
        gebruiksrechten = GebruiksrechtenFactory(
            informatieobject__latest_version__bronorganisatie=730924658,
            informatieobject__latest_version__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            omschrijving_voorwaarden="some conditions"
        )

        self.assertEqual(
            gebruiksrechten.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some conditions'
        )

    def test_oio(self):
        oio = ObjectInformatieObjectFactory(
            informatieobject__latest_version__bronorganisatie=730924658,
            informatieobject__latest_version__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            is_zaak=True
        )
        responses = {
            oio.object: {
                'url': oio.object,
                'bronorganisatie': 123456789,
                'identificatie': 'c7cf4ce7-3cbe-44ca-848b-fc6e8ea80acf'
            }
        }

        with mock_client(responses):
            unique_representation = oio.unique_representation()

        self.assertEqual(
            unique_representation,
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - c7cf4ce7-3cbe-44ca-848b-fc6e8ea80acf'
        )
