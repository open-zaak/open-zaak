import uuid
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ObjectTypes
from vng_api_common.tests import JWTAuthMixin, get_validation_errors, reverse
from zds_client.tests.mocks import mock_client

from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory, ObjectInformatieObjectFactory
)

ZAAK = 'https://zrc.nl/api/v1/zaken/1234'
BESLUIT = 'https://brc.nl/api/v1/besluiten/4321'


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class ObjectInformatieObjectTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    list_url = reverse(ObjectInformatieObject)

    def test_create_with_objecttype_zaak(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse('enkelvoudiginformatieobject-detail', kwargs={
            'uuid': eio.uuid
        })

        response = self.client.post(self.list_url, {
            'object': ZAAK,
            'informatieobject': f'http://testserver{eio_url}',
            'objectType': 'zaak'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zio = eio.canonical.objectinformatieobject_set.get()
        self.assertEqual(zio.object, ZAAK)

    def test_create_with_objecttype_besluit(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse('enkelvoudiginformatieobject-detail', kwargs={
            'uuid': eio.uuid
        })

        response = self.client.post(self.list_url, {
            'object': BESLUIT,
            'informatieobject': f'http://testserver{eio_url}',
            'objectType': 'besluit'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        bio = eio.canonical.objectinformatieobject_set.get()
        self.assertEqual(bio.object, BESLUIT)

    def test_duplicate_object(self):
        """
        Test the (informatieobject, object) unique together validation.
        """
        oio = ObjectInformatieObjectFactory.create(
            is_zaak=True,
        )
        enkelvoudig_informatie_url = reverse('enkelvoudiginformatieobject-detail', kwargs={
            'uuid': oio.informatieobject.latest_version.uuid
        })

        content = {
            'informatieobject': f'http://testserver{enkelvoudig_informatie_url}',
            'object': oio.object,
            'objectType': ObjectTypes.zaak,
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'unique')

    def test_filter(self):
        oio = ObjectInformatieObjectFactory.create(
            is_zaak=True,
        )
        eo_detail_url = reverse('enkelvoudiginformatieobject-detail', kwargs={
            'uuid': oio.informatieobject.latest_version.uuid
        })

        response = self.client.get(self.list_url, {
            'informatieobject': f'http://testserver{eo_detail_url}',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['informatieobject'], f'http://testserver{eo_detail_url}')


@patch('zds_client.client.get_operation_url')
@patch('zds_client.tests.mocks.MockClient.fetch_schema', return_value={})
class ObjectInformatieObjectDestroyTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    RESPONSES = {
        "https://zrc.nl/api/v1/zaakinformatieobjecten": [],
        "https://brc.nl/api/v1/besluitinformatieobjecten": [{
            "url": f"https://brc.nl/api/v1/besluitinformatieobjecten/{uuid.uuid4()}",
            "informatieobject": f"http://testserver/api/v1/enkelvoudiginformatieobjecten/{uuid.uuid4()}",
            "besluit": BESLUIT,
            "aardRelatieWeergave": "Legt vast, omgekeerd: is vastgelegd in",
        }],
    }

    def test_destroy_oio_remote_gone(self, mock_fetch_schema, mock_get_operation_url):
        mock_get_operation_url.return_value = '/api/v1/zaakinformatieobjecten'
        oio = ObjectInformatieObjectFactory.create(is_zaak=True, object=ZAAK)
        url = reverse(oio)

        with mock_client(responses=self.RESPONSES):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ObjectInformatieObject.objects.exists())

    def test_destroy_oio_remote_still_present(self, mock_fetch_schema, mock_get_operation_url):
        mock_get_operation_url.return_value = '/api/v1/besluitinformatieobjecten'
        oio = ObjectInformatieObjectFactory.create(is_besluit=True, object=BESLUIT)
        url = reverse(oio)

        with mock_client(responses=self.RESPONSES):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "remote-relation-exists")
