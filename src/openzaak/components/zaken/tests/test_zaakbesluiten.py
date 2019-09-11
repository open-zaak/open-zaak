from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.utils.tests import JWTAuthMixin

from .factories import ZaakFactory


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
            "zaakbesluit-detail", kwargs={"zaak_uuid": zaak.uuid, "uuid": besluit.uuid}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [
                {
                    "url": f"http://testserver{zaakbesluit_url}",
                    "uuid": str(besluit.uuid),
                    "besluit": f"http://testserver{reverse(besluit)}",
                }
            ],
        )

    def test_detail(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        BesluitFactory.create(zaak=None)  # unrelated besluit
        url = reverse(
            "zaakbesluit-detail", kwargs={"zaak_uuid": zaak.uuid, "uuid": besluit.uuid}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(besluit.uuid),
                "besluit": f"http://testserver{reverse(besluit)}",
            },
        )

    def test_create(self):
        besluit = BesluitFactory.create(for_zaak=True)
        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": besluit.zaak.uuid})

        response = self.client.post(url, {"besluit": besluit_url})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete(self):
        besluit = BesluitFactory.create(for_zaak=True)
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": besluit.zaak.uuid, "uuid": besluit.uuid},
        )
        besluit.zaak = None  # it must already be disconnected from zaak
        besluit.save()

        response = self.client.delete(url)

        # because the reference between zaak/besluit is broken, this 404s, as
        # it should
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
