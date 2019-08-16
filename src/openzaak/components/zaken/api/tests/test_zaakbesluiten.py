from unittest import skip

from openzaak.components.besluiten.models.tests.factories import BesluitFactory
from openzaak.components.zaken.models.tests.factories import (
    ZaakBesluitFactory, ZaakFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, reverse


@skip('ZaakBesluit is not implemented yet')
class ZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create()
        besluit_url = reverse(besluit)
        url = reverse('zaakbesluit-list', kwargs={'zaak_uuid': zaak.uuid})

        response = self.client.post(url, {
            'besluit': besluit_url
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zakk_besluit = zaak.zaakbesluit_set.get()
        self.assertEqual(zakk_besluit.besluit, besluit)

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
