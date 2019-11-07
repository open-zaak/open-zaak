from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.utils.tests import JWTAuthMixin

from .factories import StatusFactory


class StatusTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_filter_statussen_op_zaak(self):
        status1, status2 = StatusFactory.create_batch(2)
        assert status1.zaak != status2.zaak
        status1_url = reverse("status-detail", kwargs={"uuid": status1.uuid})
        status2_url = reverse("status-detail", kwargs={"uuid": status2.uuid})

        list_url = reverse("status-list")
        zaak_url = reverse("zaak-detail", kwargs={"uuid": status1.zaak.uuid})

        response = self.client.get(list_url, {"zaak": f"http://openzaak.nl{zaak_url}"}, HTTP_HOST="openzaak.nl")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://openzaak.nl{status1_url}")
        self.assertNotEqual(data[0]["url"], f"http://openzaak.nl{status2_url}")
