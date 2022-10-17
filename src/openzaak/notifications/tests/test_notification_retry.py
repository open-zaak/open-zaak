from unittest.mock import patch

from django.test import override_settings, tag

import celery
from freezegun import freeze_time
from notifications_api_common.tests.utils import mock_notify
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse
from zds_client import ClientError

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.zaken.models import Zaak
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS, get_operation_url
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("notifications")
@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
@patch(
    "notifications_api_common.viewsets.NotificationViewSetMixin.send_notification.delay",
    side_effect=mock_notify,
)
class NotificationRetryTestCase(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch("zds_client.Client.create", side_effect=ClientError)
    @patch(
        "notifications_api_common.viewsets.NotificationMixin.send_notification.retry"
    )
    def test_notificatie_client_error_retry(
        self, retry_mock, mock_client_create, mock_notif
    ):
        """
        Verify that a retry is called when the sending of the notification didn't succeed due to an invalid response
        """
        retry_mock.side_effect = celery.exceptions.Retry

        url = get_operation_url("zaak_create")
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        request_data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        with self.assertRaises(celery.exceptions.Retry):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(url, request_data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.data
        zaak = Zaak.objects.get()

        self.assertEqual(str(zaak.uuid), data["uuid"])
        mock_client_create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "zaken",
                "hoofdObject": data["url"],
                "resource": "zaak",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": "517439943",
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )
        retry_mock.assert_called_once()
