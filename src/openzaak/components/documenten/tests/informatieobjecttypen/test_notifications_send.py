# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import FailedNotification, NotificationResponse
from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.models import InformatieObjectType
from openzaak.components.catalogi.tests.base import APITestCase
from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
)
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.utils.urls import reverse

from ..utils import get_operation_url


@tag("notifications")
@requests_mock.Mocker()
@override_settings(
    NOTIFICATIONS_DISABLED=False,
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationsConfigMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_informatieobjecttype_create_fail_send_notification_create_db_entry(
        self, m
    ):
        url = get_operation_url("informatieobjecttype_create")

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        iot = InformatieObjectType.objects.get()

        data = response.json()
        self.assertEqual(
            data["url"], f"http://testserver{reverse(iot, namespace='documenten')}"
        )
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "informatieobjecttypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "informatieobjecttype",
            "resourceUrl": data["url"],
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_informatieobjecttype_delete_fail_send_notification_create_db_entry(
        self, m
    ):
        iotype = InformatieObjectTypeFactory.create()
        url = reverse(iotype, namespace="documenten")

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "informatieobjecttypen",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(iotype.catalogus)}",
            },
            "resource": "informatieobjecttype",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)
