from openzaak.components.besluiten.models.tests.factories import BesluitFactory
from openzaak.components.zaken.models.tests.factories import ZaakFactory
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, reverse


class ZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list(self):
        """
        Assert that it's possible to list besluiten for zaken.
        """
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        BesluitFactory.create(zaak=None)  # unrelated besluit
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})
        zaakbesluit_url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": besluit.uuid}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{
            "url": f'http://testserver{zaakbesluit_url}',
            "uuid": str(besluit.uuid),
            "besluit": f"http://testserver{reverse(besluit)}",
        }])

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
