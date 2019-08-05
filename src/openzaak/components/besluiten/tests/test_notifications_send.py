from unittest.mock import patch

from django.test import override_settings

from freezegun import freeze_time
from openzaak.components.besluiten.api.tests.mixins import MockSyncMixin
from openzaak.components.besluiten.api.tests.utils import get_operation_url
from openzaak.components.besluiten.models.constants import VervalRedenen
from openzaak.components.besluiten.models.tests.factories import (
    BesluitFactory, BesluitInformatieObjectFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin

BESLUITTYPE = 'https://ztc.com/besluittypen/1234'


@freeze_time("2018-09-07T00:00:00Z")
@override_settings(
    LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
    NOTIFICATIONS_DISABLED=False
)
class SendNotifTestCase(MockSyncMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @patch('zds_client.Client.from_url')
    def test_send_notif_create_besluit(self, mock_client, *mocks):
        """
        Check if notifications will be send when Besluit is created
        """
        client = mock_client.return_value
        url = get_operation_url('besluit_create')
        data = {
            'verantwoordelijkeOrganisatie': '517439943',  # RSIN
            'besluittype': BESLUITTYPE,
            'datum': '2018-09-06',
            'toelichting': "Vergunning verleend.",
            'ingangsdatum': '2018-10-01',
            'vervaldatum': '2018-11-01',
            'vervalreden': VervalRedenen.tijdelijk,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            'notificaties',
            {
                'kanaal': 'besluiten',
                'hoofdObject': data['url'],
                'resource': 'besluit',
                'resourceUrl': data['url'],
                'actie': 'create',
                'aanmaakdatum': '2018-09-07T00:00:00Z',
                'kenmerken': {
                    'verantwoordelijkeOrganisatie': '517439943',
                    'besluittype': BESLUITTYPE,
                }
            }
        )

    @patch('zds_client.Client.from_url')
    def test_send_notif_delete_resultaat(self, mock_client):
        """
        Check if notifications will be send when resultaat is deleted
        """
        client = mock_client.return_value
        besluit = BesluitFactory.create(besluittype=BESLUITTYPE)
        besluit_url = get_operation_url('besluit_read', uuid=besluit.uuid)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        bio_url = get_operation_url('besluitinformatieobject_delete', uuid=bio.uuid)

        response = self.client.delete(bio_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        client.create.assert_called_once_with(
            'notificaties',
            {
                'kanaal': 'besluiten',
                'hoofdObject': f'http://testserver{besluit_url}',
                'resource': 'besluitinformatieobject',
                'resourceUrl': f'http://testserver{bio_url}',
                'actie': 'destroy',
                'aanmaakdatum': '2018-09-07T00:00:00Z',
                'kenmerken': {
                    'verantwoordelijkeOrganisatie': besluit.verantwoordelijke_organisatie,
                    'besluittype': besluit.besluittype,
                }
            }
        )
