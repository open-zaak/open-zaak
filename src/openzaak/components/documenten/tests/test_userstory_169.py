"""
Test that images can be uploaded as base64 with meta information.

See:
* https://github.com/VNG-Realisatie/gemma-zaken/issues/169 (us)
* https://github.com/VNG-Realisatie/gemma-zaken/issues/182 (mapping)
"""
import base64
from io import BytesIO

from django.test import override_settings

from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import (
    JWTAuthMixin, TypeCheckMixin
)

from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN

INFORMATIEOBJECTTYPE = 'https://example.com/ztc/api/v1/catalogus/1/informatieobjecttype/1'


class US169Tests(TypeCheckMixin, JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_AANMAKEN]
    informatieobjecttype = INFORMATIEOBJECTTYPE

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_upload_image(self):
        url = get_operation_url('enkelvoudiginformatieobject_create')

        # create dummy image in memory
        image = Image.new('RGB', (1, 1), 'red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')

        image_data = base64.b64encode(image_io.getvalue())

        data = {
            'inhoud': image_data.decode('utf-8'),
            'bronorganisatie': '715832694',
            'taal': 'dut',
            'creatiedatum': '2018-07-30',
            'titel': 'bijlage.jpg',
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'auteur': 'John Doe',
            'informatieobjecttype': INFORMATIEOBJECTTYPE,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        response_data = response.json()
        self.assertIn('identificatie', response_data)

        self.assertResponseTypes(response_data, (
            ('url', str),
            ('inhoud', str),
            ('bronorganisatie', str),
            ('taal', str),
            ('creatiedatum', str),
            ('titel', str),
            ('vertrouwelijkheidaanduiding', str),
            ('auteur', str),
            ('informatieobjecttype', str),
        ))
