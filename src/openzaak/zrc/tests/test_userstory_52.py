"""
Als behandelaar wil ik locatie- en/of objectinformatie bij de melding
ontvangen, zodat ik voldoende details weet om de melding op te volgen.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/52
"""
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import (
    JWTAuthMixin, TypeCheckMixin, get_operation_url
)
from zds_client.tests.mocks import mock_client

from zrc.datamodel.models import ZaakEigenschap
from zrc.datamodel.tests.factories import ZaakEigenschapFactory, ZaakFactory

EIGENSCHAP_OBJECTTYPE = 'https://example.com/ztc/api/v1/catalogus/1/zaaktypen/1/eigenschappen/1'
EIGENSCHAP_NAAM_BOOT = 'https://example.com/ztc/api/v1/catalogus/1/zaaktypen/1/eigenschappen/2'


class US52TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_zet_eigenschappen(self, *mocks):
        zaak = ZaakFactory.create()
        url = get_operation_url('zaakeigenschap_create', zaak_uuid=zaak.uuid)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        data = {
            'zaak': zaak_url,
            'eigenschap': EIGENSCHAP_OBJECTTYPE,
            'waarde': 'overlast_water'
        }

        responses = {
            EIGENSCHAP_OBJECTTYPE: {
                'url': EIGENSCHAP_OBJECTTYPE,
                'naam': 'foobar',
            },
        }

        with mock_client(responses):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakeigenschap = ZaakEigenschap.objects.get()
        self.assertEqual(zaakeigenschap.zaak, zaak)
        detail_url = get_operation_url('zaakeigenschap_read', zaak_uuid=zaak.uuid, uuid=zaakeigenschap.uuid)
        self.assertEqual(
            response_data,
            {
                'url': f"http://testserver{detail_url}",
                'uuid': str(zaakeigenschap.uuid),
                'naam': 'foobar',
                'zaak': f"http://testserver{zaak_url}",
                'eigenschap': EIGENSCHAP_OBJECTTYPE,
                'waarde': 'overlast_water'
            }
        )

    def test_lees_eigenschappen(self):
        zaak = ZaakFactory.create()
        ZaakEigenschapFactory.create_batch(3, zaak=zaak)
        url = get_operation_url('zaakeigenschap_list', zaak_uuid=zaak.uuid)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(len(response_data), 3)
        for obj in response_data:
            with self.subTest(obj=obj):
                self.assertResponseTypes(obj, (
                    ('url', str),
                    ('naam', str),
                    ('zaak', str),
                    ('eigenschap', str),
                    ('waarde', str),
                ))
