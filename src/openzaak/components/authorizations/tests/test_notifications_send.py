from unittest.mock import patch

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding

from openzaak.components.authorizations.api.tests.utils import get_operation_url
from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import SCOPE_AUTORISATIES_BIJWERKEN
from ..models.tests.factories import AutorisatieFactory


@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_BIJWERKEN)]
    component = ComponentTypes.ac

    @patch("zds_client.Client.from_url")
    def test_send_notif_create_application(self, mock_client):
        """
        Check if notifications will be send when applicaties is created
        """
        client = mock_client.return_value
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "autorisaties",
                "hoofdObject": data["url"],
                "resource": "applicatie",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {},
            },
        )

    @patch("zds_client.Client.from_url")
    def test_send_notif_update_application(self, mock_client):
        """
        Check if notifications will be send when applicatie is updated
        """
        client = mock_client.return_value
        autorisatie = AutorisatieFactory.create(
            applicatie__client_ids=["id1", "id2"],
            zaaktype="https://example.com",
            scopes=["dummy.scope"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        applicatie = autorisatie.applicatie

        url = get_operation_url("applicatie_partial_update", uuid=applicatie.uuid)

        response = self.client.patch(url, {"client_ids": ["id1"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "autorisaties",
                "hoofdObject": data["url"],
                "resource": "applicatie",
                "resourceUrl": data["url"],
                "actie": "partial_update",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {},
            },
        )
