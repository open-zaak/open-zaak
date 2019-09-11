"""
Als behandelaar wil ik locatie- en/of objectinformatie bij de melding
ontvangen, zodat ik voldoende details weet om de melding op te volgen.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/52
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.catalogi.models.tests.factories import EigenschapFactory
from openzaak.utils.tests import JWTAuthMixin

from ..models import ZaakEigenschap
from .factories import ZaakEigenschapFactory, ZaakFactory
from .utils import get_operation_url


class US52TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zet_eigenschappen(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(eigenschapnaam="foobar")
        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": zaak_url,
            "eigenschap": eigenschap_url,
            "waarde": "overlast_water",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakeigenschap = ZaakEigenschap.objects.get()
        self.assertEqual(zaakeigenschap.zaak, zaak)
        detail_url = get_operation_url(
            "zaakeigenschap_read", zaak_uuid=zaak.uuid, uuid=zaakeigenschap.uuid
        )
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(zaakeigenschap.uuid),
                "naam": "foobar",
                "zaak": f"http://testserver{zaak_url}",
                "eigenschap": f"http://testserver{eigenschap_url}",
                "waarde": "overlast_water",
            },
        )

    def test_lees_eigenschappen(self):
        zaak = ZaakFactory.create()
        ZaakEigenschapFactory.create_batch(3, zaak=zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(len(response_data), 3)
        for obj in response_data:
            with self.subTest(obj=obj):
                self.assertResponseTypes(
                    obj,
                    (
                        ("url", str),
                        ("naam", str),
                        ("zaak", str),
                        ("eigenschap", str),
                        ("waarde", str),
                    ),
                )
