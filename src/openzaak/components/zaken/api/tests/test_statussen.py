from openzaak.components.zaken.models.tests.factories import StatusFactory
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, reverse


class StatusTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_filter_statussen_op_zaak(self):
        status1, status2 = StatusFactory.create_batch(2)
        assert status1.zaak != status2.zaak
        status1_url = reverse('status-detail', kwargs={'uuid': status1.uuid})
        status2_url = reverse('status-detail', kwargs={'uuid': status2.uuid})

        list_url = reverse('status-list')

        response = self.client.get(list_url, {
            'zaak': reverse('zaak-detail', kwargs={'uuid': status1.zaak.uuid})
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['url'],
            f"http://testserver{status1_url}"
        )
        self.assertNotEqual(
            response.data[0]['url'],
            f"http://testserver{status2_url}"
        )
