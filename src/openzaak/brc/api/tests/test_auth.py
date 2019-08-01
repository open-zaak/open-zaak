"""
Guarantee that the proper authorization amchinery is in place.
"""
from unittest.mock import patch
from unittest import skip

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import AuthCheckMixin, JWTAuthMixin, reverse

from openzaak.brc.datamodel.models import BesluitInformatieObject
from openzaak.brc.datamodel.tests.factories import (
    BesluitFactory, BesluitInformatieObjectFactory
)

from ..scopes import SCOPE_BESLUITEN_AANMAKEN, SCOPE_BESLUITEN_ALLES_LEZEN
from .mixins import MockSyncMixin


@skip('Current implementation is without authentication')
@override_settings(ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient')
class BesluitScopeForbiddenTests(MockSyncMixin, AuthCheckMixin, APITestCase):

    def test_cannot_create_besluit_without_correct_scope(self):
        url = reverse('besluit-list')
        self.assertForbidden(url, method='post')

    def test_cannot_read_without_correct_scope(self):
        besluit = BesluitFactory.create()
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        urls = [
            reverse('besluit-list'),
            reverse(besluit),
            reverse('besluitinformatieobject-list'),
            reverse(bio)
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method='get')


@skip('Current implementation is without authentication')
class BesluitReadCorrectScopeTests(MockSyncMixin, JWTAuthMixin, APITestCase):
    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
    besluittype = 'https://besluittype.nl/ok'

    def test_besluit_list(self):
        """
        Assert you can only list BESLUITen of the besluittypes of your authorization
        """
        BesluitFactory.create(besluittype='https://besluittype.nl/ok')
        BesluitFactory.create(besluittype='https://besluittype.nl/not_ok')
        url = reverse('besluit-list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['besluittype'], 'https://besluittype.nl/ok')

    def test_besluit_retreive(self):
        """
        Assert you can only read BESLUITen of the besluittypes of your authorization
        """
        besluit1 = BesluitFactory.create(besluittype='https://besluittype.nl/ok')
        besluit2 = BesluitFactory.create(besluittype='https://besluittype.nl/not_ok')
        url1 = reverse(besluit1)
        url2 = reverse(besluit2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        BesluitFactory.create(besluittype='https://besluittype.nl/ok')
        BesluitFactory.create(besluittype='https://besluittype.nl/not_ok')
        url = reverse('besluit-list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()['results']
        self.assertEqual(len(response_data), 2)


@skip('Current implementation is without authentication')
@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class BioReadTests(MockSyncMixin, JWTAuthMixin, APITestCase):

    scopes = [SCOPE_BESLUITEN_ALLES_LEZEN, SCOPE_BESLUITEN_AANMAKEN]
    besluittype = 'https://besluittype.nl/ok'

    def test_list_bio_limited_to_authorized_zaken(self):
        besluit1 = BesluitFactory.create(besluittype='https://besluittype.nl/ok')
        besluit2 = BesluitFactory.create(besluittype='https://besluittype.nl/not_ok')

        url = reverse(BesluitInformatieObject)

        # must show up
        bio1 = BesluitInformatieObjectFactory.create(besluit=besluit1)
        # must not show up
        bio2 = BesluitInformatieObjectFactory.create(besluit=besluit2)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)

        besluit_url = reverse(bio1.besluit)
        self.assertEqual(response_data[0]['besluit'], f'http://testserver{besluit_url}')

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_bio_limited_to_authorized_besluiten(self, *mocks):
        informatieobject = 'https://drc.com/api/v1/enkelvoudigeinformatieobjecten/1234'

        besluit1 = BesluitFactory.create(besluittype='https://besluittype.nl/ok')
        besluit2 = BesluitFactory.create(besluittype='https://besluittype.nl/not_ok')

        besluit_uri1 = reverse(besluit1)
        besluit_url1 = f'http://testserver{besluit_uri1}'

        besluit_uri2 = reverse(besluit2)
        besluit_url2 = f'http://testserver{besluit_uri2}'

        url1 = reverse('besluitinformatieobject-list')
        url2 = reverse('besluitinformatieobject-list')

        data1 = {
            'informatieobject': informatieobject,
            'besluit': besluit_url1
        }
        data2 = {
            'informatieobject': informatieobject,
            'besluit': besluit_url2
        }

        response1 = self.client.post(url1, data1)
        response2 = self.client.post(url2, data2)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED, response1.data)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN, response2.data)
