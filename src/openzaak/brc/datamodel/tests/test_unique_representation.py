from django.test import override_settings

from rest_framework.test import APITestCase
from zds_client.tests.mocks import mock_client

from openzaak.brc.api.tests.mixins import MockSyncMixin

from .factories import BesluitFactory, BesluitInformatieObjectFactory


@override_settings(
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class UniqueRepresentationTestCase(MockSyncMixin, APITestCase):

    def test_besluit(self):
        besluit = BesluitFactory(
            identificatie='5d940d52-ff5e-4b18-a769-977af9130c04'
        )

        self.assertEqual(
            besluit.unique_representation(),
            '5d940d52-ff5e-4b18-a769-977af9130c04'
        )

    def test_besluitinformatieobject(self):
        bio = BesluitInformatieObjectFactory(
            besluit__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04'
        )
        responses = {
            bio.informatieobject: {
                'url': bio.informatieobject,
                'identificatie': "12345",
            }
        }
        with mock_client(responses):
            unique_representation = bio.unique_representation()

        self.assertEqual(
            unique_representation,
            '(5d940d52-ff5e-4b18-a769-977af9130c04) - 12345'
        )
