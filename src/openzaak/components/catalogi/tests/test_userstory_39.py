"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""
from openzaak.components.catalogi.api.tests.base import ClientAPITestMixin
from openzaak.components.catalogi.api.tests.utils import get_operation_url
from openzaak.components.catalogi.models.tests.factories import (
    StatusTypeFactory, ZaakTypeFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin


class US39TestCase(TypeCheckMixin, ClientAPITestMixin, APITestCase):

    def test_retrieve_zaaktype(self):
        zaaktype = ZaakTypeFactory.create()
        url = get_operation_url(
            'zaaktype_read',
            catalogus_uuid=zaaktype.catalogus.uuid,
            uuid=zaaktype.uuid
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['url'], f"http://testserver{url}")

        self.assertResponseTypes(response_data, (
            ('identificatie', int),
            ('omschrijving', str),
            ('omschrijvingGeneriek', str),
            ('catalogus', str),
            ('statustypen', list),
        ))

        self.assertIsInstance(response_data['omschrijving'], str)

    def test_retrieve_statustype(self):
        statustype = StatusTypeFactory.create()
        url = get_operation_url(
            'statustype_read',
            catalogus_uuid=statustype.zaaktype.catalogus.uuid,
            zaaktype_uuid=statustype.zaaktype.uuid,
            uuid=statustype.uuid
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['url'], f"http://testserver{url}")

        types = [
            ('omschrijving', str),
            ('omschrijvingGeneriek', str),
            ('statustekst', str),
            ('zaaktype', str),
        ]
        self.assertResponseTypes(response_data, types)
