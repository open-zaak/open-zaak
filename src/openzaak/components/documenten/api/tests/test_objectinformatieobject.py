import uuid
from unittest import expectedFailure, skip

from django.test import override_settings, tag

from openzaak.components.besluiten.models.tests.factories import (
    BesluitFactory, BesluitInformatieObjectFactory
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory, ObjectInformatieObjectFactory
)
from openzaak.components.zaken.models.tests.factories import (
    ZaakFactory, ZaakInformatieObjectFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ObjectTypes
from vng_api_common.tests import (
    JWTAuthMixin, get_validation_errors, reverse, reverse_lazy
)
from zds_client.tests.mocks import mock_client

ZAAK = 'https://zrc.nl/api/v1/zaken/1234'
BESLUIT = 'https://brc.nl/api/v1/besluiten/4321'


@tag("oio")
@skip('ObjectInformatieObject is not implemented yet')
@override_settings(ALLOWED_HOSTS=["testserver.nl"])
class ObjectInformatieObjectTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy("objectinformatieobject-list")

    def test_create_with_objecttype_zaak(self):
        zaak = ZaakFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        # relate the two
        zio = ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=eio.canonical)
        zaak_url = reverse(zaak)
        eio_url = reverse(eio)
        # re-use the ZIO UUID for OIO
        zio_url = reverse("objectinformatieobject-detail", kwargs={"uuid": zio.uuid})

        response = self.client.post(self.list_url, {
            'object': f"http://testserver.nl{zaak_url}",
            'informatieobject': f'http://testserver.nl{eio_url}',
            'objectType': 'zaak'
        }, HTTP_HOST="testserver.nl")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data, {
            "url": f"http://testserver.nl{zio_url}",
            "informatieobject": f"http://testserver.nl{eio_url}",
            "object": f"http://testserver.nl{zaak_url}",
            "object_type": "zaak",
        })

    def test_create_with_objecttype_besluit(self):
        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        # relate the two
        bio = BesluitInformatieObjectFactory.create(besluit=besluit, informatieobject=eio.canonical)
        besluit_url = reverse(besluit)
        eio_url = reverse(eio)
        # re-use the ZIO UUID for OIO
        bio_url = reverse("objectinformatieobject-detail", kwargs={"uuid": bio.uuid})

        response = self.client.post(self.list_url, {
            'object': f"http://testserver.nl{besluit_url}",
            'informatieobject': f'http://testserver{eio_url}',
            'objectType': 'besluit'
        }, HTTP_HOST="testserver.nl")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {
            "url": f"http://testserver.nl{bio_url}",
            "object": f"http://testserver.nl{besluit_url}",
            "informatieobject": f"http://testserver.nl{eio_url}",
            "object_type": "besluit",
        })

    @expectedFailure
    def test_duplicate_object(self):
        """
        Test the (informatieobject, object) unique together validation.

        This is expected to fail, since there is no actual creation in database.
        It will however become relevant again when we're handling remote
        references.
        """
        zio = ZaakInformatieObjectFactory.create()

        eio_url = reverse(zio.informatieobject.latest_version)
        zaak_url = reverse(zio.zaak)

        content = {
            'informatieobject': f'http://testserver.nl{eio_url}',
            'object': f"http://testserver.nl{zaak_url}",
            'objectType': ObjectTypes.zaak,
        }

        # Send to the API
        response = self.client.post(self.list_url, content, HTTP_HOST="testserver.nl")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'unique')

    def test_filter(self):
        zio = ZaakInformatieObjectFactory.create()
        eio_detail_url = reverse(zio.informatieobject.latest_version)

        response = self.client.get(self.list_url, {
            'informatieobject': f'http://testserver.nl{eio_detail_url}',
        }, HTTP_HOST="testserver.nl")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['informatieobject'], f'http://testserver{eio_detail_url}')


@skip('ObjectInformatieObject is not implemented yet')
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
        # self.assertFalse(ObjectInformatieObject.objects.exists())

    def test_destroy_oio_remote_still_present(self, mock_fetch_schema, mock_get_operation_url):
        mock_get_operation_url.return_value = '/api/v1/besluitinformatieobjecten'
        oio = ObjectInformatieObjectFactory.create(is_besluit=True, object=BESLUIT)
        url = reverse(oio)

        with mock_client(responses=self.RESPONSES):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "remote-relation-exists")
