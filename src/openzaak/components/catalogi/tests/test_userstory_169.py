"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39

Zie ook:

* https://github.com/VNG-Realisatie/gemma-zaken/issues/45
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin

from openzaak.components.catalogi.api.tests.base import ClientAPITestMixin
from openzaak.components.catalogi.api.tests.utils import get_operation_url
from openzaak.components.catalogi.models.tests.factories import ZaakTypeFactory


class US169TestCase(TypeCheckMixin, ClientAPITestMixin, APITestCase):

    def test_ophalen_servicenorm_doorlooptijd(self):
        zaaktype = ZaakTypeFactory.create()
        url = get_operation_url(
            'zaaktype_read',
            catalogus_uuid=zaaktype.catalogus.uuid,
            uuid=zaaktype.uuid
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertResponseTypes(response_data, (
            ('doorlooptijd', str),
            ('servicenorm', type(None)),
        ))

        self.assertEqual(response_data['doorlooptijd'], 'P30D')
