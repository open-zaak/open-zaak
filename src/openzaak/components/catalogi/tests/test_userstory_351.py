"""
Test zaak afsluiten
Zie: https://github.com/VNG-Realisatie/gemma-zaken/issues/351
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin

from openzaak.components.catalogi.api.tests.base import ClientAPITestMixin
from openzaak.components.catalogi.api.tests.utils import get_operation_url
from openzaak.components.catalogi.models.tests.factories import (
    RolTypeFactory, StatusTypeFactory, ZaakTypeFactory
)


class US351TestCase(TypeCheckMixin, ClientAPITestMixin, APITestCase):

    def test_is_eindstatus(self):
        zaaktype = ZaakTypeFactory.create()

        rol_type = RolTypeFactory.create(zaaktype=zaaktype)

        statustype_1 = StatusTypeFactory.create(
            zaaktype=zaaktype,
            roltypen=[rol_type, ],
            statustypevolgnummer=1
        )
        statustype_2 = StatusTypeFactory.create(
            zaaktype=zaaktype,
            roltypen=[rol_type, ],
            statustypevolgnummer=2
        )

        # Volgnummer 1
        url = get_operation_url(
            'statustype_read',
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
            uuid=statustype_1.uuid,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertFalse(response_data['isEindstatus'])

        # Volgnummer 2
        url = get_operation_url(
            'statustype_read',
            catalogus_uuid=zaaktype.catalogus.uuid,
            zaaktype_uuid=zaaktype.uuid,
            uuid=statustype_2.uuid
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertTrue(response_data['isEindstatus'])
