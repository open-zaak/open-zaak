# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.contrib.sites.models import Site
from django.test import override_settings, tag

import requests_mock
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from notifications_api_common.tasks import NotificationException, send_notification
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@tag("notifications")
@require_cmis
@freeze_time("2018-09-07T00:00:00Z")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=True)
@patch("notifications_api_common.viewsets.send_notification.delay")
class SendNotifTestCase(NotificationsConfigMixin, JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_send_notif_delete_besluitinformatieobject(self, mock_notif):
        """
        Check if notifications will be send when besluitinformatieobject is deleted
        """

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)
        bio_path = reverse(bio)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(bio_path)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        mock_notif.assert_called_with(
            {
                "kanaal": "besluiten",
                "hoofdObject": f"http://testserver{reverse(bio.besluit)}",
                "resource": "besluitinformatieobject",
                "resourceUrl": f"http://testserver{bio_path}",
                "actie": "destroy",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": bio.besluit.verantwoordelijke_organisatie,
                    "besluittype": f"http://testserver{reverse(bio.besluit.besluittype)}",
                    "besluittype.catalogus": f"http://testserver{reverse(bio.besluit.besluittype.catalogus)}",
                },
            }
        )


@tag("notifications", "DEPRECATED")
@requests_mock.Mocker(real_http=True)  # for CMIS requests
@require_cmis
@freeze_time("2019-01-01T12:00:00Z")
@override_settings(
    NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS, CMIS_ENABLED=True
)
@patch("notifications_api_common.viewsets.send_notification.delay")
class FailedNotificationCMISTests(
    NotificationsConfigMixin, JWTAuthMixin, APICMISTestCase
):
    heeft_alle_autorisaties = True
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def test_besluitinformatieobject_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("besluitinformatieobject_create")

        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        besluit = BesluitFactory.create()
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit)
        data = {
            "informatieobject": io_url,
            "besluit": f"http://testserver{besluit_url}",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(besluit)}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(besluit.besluittype)}",
                "besluittype.catalogus": f"http://testserver{reverse(besluit.besluittype.catalogus)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": data["url"],
        }

        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, celery retry is called
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluitinformatieobject_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()

        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)
        url = reverse(bio)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(bio.besluit)}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": bio.besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(bio.besluit.besluittype)}",
                "besluittype.catalogus": f"http://testserver{reverse(bio.besluit.besluittype.catalogus)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": f"http://testserver{url}",
        }
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, celery retry is called
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
