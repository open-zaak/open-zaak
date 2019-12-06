from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.besluiten.tests.utils import get_besluit_response
from openzaak.utils.tests import JWTAuthMixin

from ..models import ZaakBesluit
from .factories import ZaakFactory


class InternalZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list(self):
        """
        Assert that it's possible to list besluiten for zaken.
        """
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        # get ZaakBesluit created via signals
        zaakbesluit = ZaakBesluit.objects.get()
        zaakbesluit_url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
        )
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [
                {
                    "url": f"http://testserver{zaakbesluit_url}",
                    "uuid": str(zaakbesluit.uuid),
                    "besluit": f"http://testserver{reverse(besluit)}",
                }
            ],
        )

    def test_detail(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        # get ZaakBesluit created via signals
        zaakbesluit = ZaakBesluit.objects.get()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakbesluit.uuid),
                "besluit": f"http://testserver{reverse(besluit)}",
            },
        )

    def test_create(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(url, {"besluit": f"http://testserver{besluit_url}"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ZaakBesluit.objects.count(), 1)

    def test_delete(self):
        besluit = BesluitFactory.create(for_zaak=True)
        zaakbesluit = ZaakBesluit.objects.get()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaakbesluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )
        besluit.zaak = None
        besluit.save()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    besluit = "https://externe.catalogus.nl/api/v1/besluiten/b71f72ef-198d-44d8-af64-ae1932df830a"
    besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/7ef7d016-b766-4456-a90c-8908eeb19b49"

    def test_create(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker(real_http=True) as m:
            m.get(
                self.besluit,
                json=get_besluit_response(self.besluit, self.besluittype, zaak_url),
            )

            response = self.client.post(url, data={"besluit": self.besluit})

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

            zaakbesluit = ZaakBesluit.objects.get()

            self.assertEqual(zaakbesluit.zaak, zaak)
            self.assertEqual(zaakbesluit.besluit, self.besluit)

    def test_delete(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker(real_http=True) as m:
            m.get(
                self.besluit,
                json=get_besluit_response(self.besluit, self.besluittype, zaak_url),
            )

            zaakbesluit = ZaakBesluit.objects.create(zaak=zaak, besluit=self.besluit)
            url = reverse(
                "zaakbesluit-detail",
                kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
            )

            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
