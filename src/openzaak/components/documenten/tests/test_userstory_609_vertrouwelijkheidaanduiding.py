"""
Test value of vertrouwelijkheidaanduiding while creating EnkelvoudigInformatieObject

See:
https://github.com/VNG-Realisatie/gemma-zaken/issues/609
"""
from base64 import b64encode

from django.test import override_settings, tag

from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import JWTAuthMixin, TypeCheckMixin, reverse
from zds_client.tests.mocks import mock_client

INFORMATIEOBJECTTYPE = 'https://example.com/ztc/api/v1/catalogus/1/informatieobjecttype/1'


@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient'
)
class US609TestCase(TypeCheckMixin, JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_AANMAKEN]
    informatieobjecttype = INFORMATIEOBJECTTYPE

    @tag('mock_client')
    def test_vertrouwelijkheidaanduiding_derived(self):
        """
        Assert that the default vertrouwelijkheidaanduiding is set
        from informatieobjecttype
        """
        url = reverse('enkelvoudiginformatieobject-list')
        responses = {
            INFORMATIEOBJECTTYPE: {
                'url': INFORMATIEOBJECTTYPE,
                'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            }
        }

        with mock_client(responses):
            response = self.client.post(url, {
                'bronorganisatie': '159351741',
                'creatiedatum': '2018-06-27',
                'titel': 'detailed summary',
                'auteur': 'test_auteur',
                'formaat': 'txt',
                'taal': 'eng',
                'bestandsnaam': 'dummy.txt',
                'inhoud': b64encode(b'some file content').decode('utf-8'),
                'link': 'http://een.link',
                'beschrijving': 'test_beschrijving',
                'informatieobjecttype': INFORMATIEOBJECTTYPE
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['vertrouwelijkheidaanduiding'],
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )

    def test_vertrouwelijkheidaanduiding_explicit(self):
        """
        Assert the explicit set of vertrouwelijkheidaanduiding
        """
        url = reverse('enkelvoudiginformatieobject-list')
        responses = {
            INFORMATIEOBJECTTYPE: {
                'url': INFORMATIEOBJECTTYPE,
                'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            }
        }

        with mock_client(responses):
            response = self.client.post(url, {
                'bronorganisatie': '159351741',
                'creatiedatum': '2018-06-27',
                'titel': 'detailed summary',
                'auteur': 'test_auteur',
                'formaat': 'txt',
                'taal': 'eng',
                'bestandsnaam': 'dummy.txt',
                'inhoud': b64encode(b'some file content').decode('utf-8'),
                'link': 'http://een.link',
                'beschrijving': 'test_beschrijving',
                'informatieobjecttype': INFORMATIEOBJECTTYPE,
                'vertrouwelijkheidaanduiding': 'openbaar'
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['vertrouwelijkheidaanduiding'],
            VertrouwelijkheidsAanduiding.openbaar,
        )
