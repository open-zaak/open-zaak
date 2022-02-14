# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings

import requests_mock
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.notifications.models import NotificationsConfig
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_oas_get
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS
from openzaak.utils.tests import JWTAuthMixin

from ..constants import VervalRedenen
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@requests_mock.Mocker()
@freeze_time("2018-09-07T00:00:00Z")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(NotificationServiceMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @patch("zds_client.Client.from_url")
    def test_send_notif_create_besluit(self, m, mock_client):
        """
        Check if notifications will be send when Besluit is created
        """
        mock_oas_get(m)
        client = mock_client.return_value
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        with capture_on_commit_callbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "besluiten",
                "hoofdObject": data["url"],
                "resource": "besluit",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": "517439943",
                    "besluittype": f"http://testserver{besluittype_url}",
                },
            },
        )

    @patch("zds_client.Client.from_url")
    def test_send_notif_delete_resultaat(self, m, mock_client):
        """
        Check if notifications will be send when resultaat is deleted
        """
        mock_oas_get(m)
        client = mock_client.return_value
        besluit = BesluitFactory.create()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        besluittype_url = reverse(besluit.besluittype)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        bio_url = get_operation_url("besluitinformatieobject_delete", uuid=bio.uuid)

        with capture_on_commit_callbacks(execute=True):
            response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        client.create.assert_called_once_with(
            "notificaties",
            {
                "kanaal": "besluiten",
                "hoofdObject": f"http://testserver{besluit_url}",
                "resource": "besluitinformatieobject",
                "resourceUrl": f"http://testserver{bio_url}",
                "actie": "destroy",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                    "besluittype": f"http://testserver{besluittype_url}",
                },
            },
        )


@requests_mock.Mocker()
@override_settings(
    NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS, CMIS_ENABLED=False
)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationServiceMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_besluit_create_fail_send_notification_create_db_entry(self, m):
        mock_oas_get(m)
        m.post(
            f"{NotificationsConfig.get_solo().api_root}notificaties", status_code=403
        )
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        with capture_on_commit_callbacks(execute=True):
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
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": data["verantwoordelijkeOrganisatie"],
                "besluittype": f"http://testserver{besluittype_url}",
            },
            "resource": "besluit",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluit_delete_fail_send_notification_create_db_entry(self, m):
        mock_oas_get(m)
        m.post(
            f"{NotificationsConfig.get_solo().api_root}notificaties", status_code=403
        )
        besluit = BesluitFactory.create()
        url = reverse(besluit)

        with capture_on_commit_callbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(besluit.besluittype)}",
            },
            "resource": "besluit",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluitinformatieobject_create_fail_send_notification_create_db_entry(
        self, m
    ):
        mock_oas_get(m)
        m.post(
            f"{NotificationsConfig.get_solo().api_root}notificaties", status_code=403
        )
        url = get_operation_url("besluitinformatieobject_create")

        besluit = BesluitFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit)
        io_url = reverse(io)
        data = {
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        with capture_on_commit_callbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(besluit)}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(besluit.besluittype)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluitinformatieobject_delete_fail_send_notification_create_db_entry(
        self, m
    ):
        mock_oas_get(m)
        m.post(
            f"{NotificationsConfig.get_solo().api_root}notificaties", status_code=403
        )
        bio = BesluitInformatieObjectFactory.create()
        url = reverse(bio)

        with capture_on_commit_callbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(bio.besluit)}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": bio.besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(bio.besluit.besluittype)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
