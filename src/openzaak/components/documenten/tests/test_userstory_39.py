"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""
import base64
from datetime import date
from urllib.parse import urlparse

from django.test import override_settings

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import JWTAuthMixin

from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN, SCOPE_DOCUMENTEN_ALLES_LEZEN
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory
)

INFORMATIEOBJECTTYPE = 'https://example.com/ztc/api/v1/catalogus/1/informatieobjecttype/1'


@temp_private_root()
class US39TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_AANMAKEN]
    informatieobjecttype = INFORMATIEOBJECTTYPE

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_create_enkelvoudiginformatieobject(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        url = get_operation_url('enkelvoudiginformatieobject_create')
        data = {
            'identificatie': 'AMS20180701001',
            'bronorganisatie': '159351741',
            'creatiedatum': '2018-07-01',
            'titel': 'text_extra.txt',
            'auteur': 'ANONIEM',
            'formaat': 'text/plain',
            'taal': 'dut',
            'inhoud': base64.b64encode(b'Extra tekst in bijlage').decode('utf-8'),
            'informatieobjecttype': INFORMATIEOBJECTTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(eio.identificatie, 'AMS20180701001')
        self.assertEqual(eio.creatiedatum, date(2018, 7, 1))

        download_url = urlparse(response.data['inhoud'])

        self.assertTrue(
            download_url.path,
            get_operation_url('enkelvoudiginformatieobject_download', uuid=eio.uuid)
        )

    def test_read_detail_file(self):
        self.autorisatie.scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
        self.autorisatie.save()

        eio = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=INFORMATIEOBJECTTYPE)
        file_url = get_operation_url('enkelvoudiginformatieobject_download', uuid=eio.uuid)

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode("utf-8"), 'some data')

    def test_list_file(self):
        self.autorisatie.scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
        self.autorisatie.save()

        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype=INFORMATIEOBJECTTYPE
        )
        list_url = get_operation_url('enkelvoudiginformatieobject_list')

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data['results']
        download_url = urlparse(data[0]['inhoud'])

        self.assertEqual(
            download_url.path,
            get_operation_url('enkelvoudiginformatieobject_download', uuid=eio.latest_version.uuid)
        )
