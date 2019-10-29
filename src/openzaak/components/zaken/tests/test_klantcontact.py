from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.utils.tests import JWTAuthMixin

from .factories import KlantContactFactory


class KlantContactFactoryTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_list_klantcontact(self):
        KlantContactFactory.create_batch(2)
        list_url = reverse("klantcontact-list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 2)
