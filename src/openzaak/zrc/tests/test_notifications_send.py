from unittest.mock import patch

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import JWTAuthMixin, get_operation_url

from zrc.api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
)
from zrc.datamodel.tests.factories import ResultaatFactory, ZaakFactory

from .utils import ZAAK_WRITE_KWARGS

VERANTWOORDELIJKE_ORGANISATIE = '517439943'

# ZTC
ZTC_ROOT = 'https://example.com/ztc/api/v1'
CATALOGUS = f'{ZTC_ROOT}/catalogus/878a3318-5950-4642-8715-189745f91b04'
ZAAKTYPE = f'{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f'
RESULTAATTYPE = f'{ZAAKTYPE}/resultaattypen/5b348dbf-9301-410b-be9e-83723e288785'


@freeze_time("2012-01-14")
@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    NOTIFICATIONS_DISABLED=False
)
class SendNotifTestCase(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @patch('zds_client.Client.from_url')
    def test_send_notif_create_zaak(self, mock_client, *mocks):
        """
        Check if notifications will be send when zaak is created
        """
        client = mock_client.return_value
        url = get_operation_url('zaak_create')
        data = {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': VERANTWOORDELIJKE_ORGANISATIE,
            'registratiedatum': '2012-01-13',
            'startdatum': '2012-01-13',
            'toelichting': 'Een stel dronken toeristen speelt versterkte '
                           'muziek af vanuit een gehuurde boot.',
            'zaakgeometrie': {
                'type': 'Point',
                'coordinates': [
                    4.910649523925713,
                    52.37240093589432
                ]
            }
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            'notificaties',
            {
                'kanaal': 'zaken',
                'hoofdObject': data['url'],
                'resource': 'zaak',
                'resourceUrl': data['url'],
                'actie': 'create',
                'aanmaakdatum': '2012-01-14T00:00:00Z',
                'kenmerken': {
                    'bronorganisatie': '517439943',
                    'zaaktype': ZAAKTYPE,
                    'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
                }
            }
        )

    @patch('zds_client.Client.from_url')
    def test_send_notif_delete_resultaat(self, mock_client):
        """
        Check if notifications will be send when resultaat is deleted
        """
        client = mock_client.return_value
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = get_operation_url('zaak_read', uuid=zaak.uuid)
        resultaat = ResultaatFactory.create(zaak=zaak)
        resultaat_url = get_operation_url('resultaat_update', uuid=resultaat.uuid)

        response = self.client.delete(resultaat_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        client.create.assert_called_once_with(
            'notificaties',
            {
                'kanaal': 'zaken',
                'hoofdObject': f'http://testserver{zaak_url}',
                'resource': 'resultaat',
                'resourceUrl': f'http://testserver{resultaat_url}',
                'actie': 'destroy',
                'aanmaakdatum': '2012-01-14T00:00:00Z',
                'kenmerken': {
                    'bronorganisatie': zaak.bronorganisatie,
                    'zaaktype': zaak.zaaktype,
                    'vertrouwelijkheidaanduiding': zaak.vertrouwelijkheidaanduiding,
                }
            }
        )
