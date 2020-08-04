# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings

from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS
from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import SCOPE_AUTORISATIES_BIJWERKEN
from .factories import ApplicatieFactory, AutorisatieFactory
from .utils import get_operation_url


@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(NotificationServiceMixin, JWTAuthMixin, APITestCase):
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


@override_settings(NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationServiceMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_applicatie_create_fail_send_notification_create_db_entry(self):
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "autorisaties",
            "kenmerken": {},
            "resource": "applicatie",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_applicatie_delete_fail_send_notification_create_db_entry(self):
        applicatie = ApplicatieFactory.create()
        url = reverse(applicatie)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "autorisaties",
            "kenmerken": {},
            "resource": "applicatie",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
