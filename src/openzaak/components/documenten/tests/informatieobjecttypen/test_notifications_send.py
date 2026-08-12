# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import call, patch

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import FailedNotification, NotificationResponse
from privates.test import temp_private_root
from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.models import InformatieObjectType
from openzaak.components.catalogi.tests.base import APITestCase
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    InformatieObjectTypeFactory,
)
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.utils.urls import reverse


@tag("notifications")
@freeze_time("2018-09-07T00:00:00Z")
@temp_private_root()
@override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class InformatieObjectTypeSendNotifTestCase(NotificationsConfigMixin, APITestCase):
    heeft_alle_autorisaties = True
    NAMESPACE = "documenten"

    def test_send_notif_create_informatieobjecttype(self, mock_notif):
        catalogus = CatalogusFactory.create()
        catalogus_url = reverse(catalogus)
        url = reverse(InformatieObjectType, namespace=self.NAMESPACE)

        data = {
            "catalogus": f"http://testserver{catalogus_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        iot = InformatieObjectType.objects.get()
        self.assertEqual(
            data["url"],
            f"http://testserver{reverse(iot, namespace=self.NAMESPACE)}",
        )
        mock_notif.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "informatieobjecttypen",
                        "hoofdObject": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "resource": "informatieobjecttype",
                        "resourceUrl": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "actie": "create",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "catalogus": f"http://testserver{catalogus_url}",
                        },
                    },
                    None,
                ),
            ]
        )

    def test_send_notif_update_informatieobjecttype(self, mock_notif):
        iot = InformatieObjectTypeFactory.create()
        url = reverse(iot, namespace=self.NAMESPACE)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {"omschrijving": "Blabla"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        self.assertEqual(
            data["url"],
            f"http://testserver{reverse(iot, namespace=self.NAMESPACE)}",
        )
        mock_notif.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "informatieobjecttypen",
                        "hoofdObject": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "resource": "informatieobjecttype",
                        "resourceUrl": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "actie": "partial_update",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "catalogus": f"http://testserver{reverse(iot.catalogus)}",
                        },
                    },
                    None,
                ),
            ]
        )

    def test_send_notif_delete_informatieobjecttype(self, mock_notif):
        iot = InformatieObjectTypeFactory.create()
        url = reverse(iot, namespace=self.NAMESPACE)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        mock_notif.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "informatieobjecttypen",
                        "hoofdObject": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "resource": "informatieobjecttype",
                        "resourceUrl": f"http://testserver{reverse(iot, namespace='documenten')}",
                        "actie": "destroy",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "catalogus": f"http://testserver{reverse(iot.catalogus)}",
                        },
                    },
                    None,
                ),
            ]
        )


@tag("notifications")
@requests_mock.Mocker()
@override_settings(
    NOTIFICATIONS_DISABLED=False,
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2019-01-01T12:00:00Z")
class InformatieObjectTypeFailedNotificationTests(
    NotificationsConfigMixin, APITestCase
):
    heeft_alle_autorisaties = True
    maxDiff = None
    NAMESPACE = "catalogi"

    def test_informatieobjecttype_create_fail_send_notification_create_db_entry(
        self, m
    ):
        url = reverse(InformatieObjectType, namespace=self.NAMESPACE)

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
            data["url"], f"http://testserver{reverse(iot, namespace=self.NAMESPACE)}"
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
        url = reverse(iotype, namespace=self.NAMESPACE)

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
