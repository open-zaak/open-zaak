# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import NotificationsConfig
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.zaken.models import Zaak
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS, get_operation_url
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin
from openzaak.tests.utils.urls import reverse

from . import mock_notification_send

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("notifications")
@requests_mock.Mocker()
@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False, CELERY_TASK_ALWAYS_EAGER=True)
@patch("notifications_api_common.viewsets.send_notification.retry")
class NotificationCeleryRetryTestCase(
    NotificationsConfigMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    def test_notificatie_client_error_retry(self, m, retry_mock):
        """
        Verify that a retry is called when the sending of the notification didn't
        succeed due to an invalid response
        """
        config = NotificationsConfig.get_solo()
        config.notification_delivery_max_retries = 3
        config.save()

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

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, request_data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.data
        zaak = Zaak.objects.get()
        message = {
            "kanaal": "zaken",
            "hoofdObject": data["url"],
            "resource": "zaak",
            "resourceUrl": data["url"],
            "actie": "create",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {
                "bronorganisatie": "517439943",
                "zaaktype": f"http://testserver{zaaktype_url}",
                "zaaktype.catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
        }

        self.assertEqual(str(zaak.uuid), data["uuid"])
        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(retry_mock.call_count, 1)
