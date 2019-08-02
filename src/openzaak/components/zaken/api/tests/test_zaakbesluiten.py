from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin

from openzaak.components.zaken.models.tests.factories import ZaakBesluitFactory, ZaakFactory

from .utils import reverse

BESLUIT = 'https://brc.nl/api/v1/besluiten/1234'


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.ObjectInformatieObjectClient'
)
class ZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create(self):
        zaak = ZaakFactory.create()
        url = reverse('zaakbesluit-list', kwargs={'zaak_uuid': zaak.uuid})

        response = self.client.post(url, {
            'besluit': BESLUIT
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zakk_besluit = zaak.zaakbesluit_set.get()
        self.assertEqual(zakk_besluit.besluit, BESLUIT)

    def test_delete(self):
        zakk_besluit = ZaakBesluitFactory.create()
        zaak = zakk_besluit.zaak
        url = reverse('zaakbesluit-detail', kwargs={
            'zaak_uuid': zaak.uuid,
            'uuid': zakk_besluit.uuid
        })

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(zaak.zaakinformatieobject_set.exists())
