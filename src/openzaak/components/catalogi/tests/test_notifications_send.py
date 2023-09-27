# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag

import requests_mock
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from notifications_api_common.tasks import NotificationException, send_notification
from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS

from ..constants import AardRelatieChoices, InternExtern
from .base import APITestCase
from .factories import BesluitTypeFactory, InformatieObjectTypeFactory, ZaakTypeFactory
from .utils import get_operation_url


@tag("notifications", "DEPRECATED")
@requests_mock.Mocker()
@override_settings(NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS)
@freeze_time("2019-01-01T12:00:00Z")
@patch("notifications_api_common.viewsets.send_notification.delay")
class FailedNotificationTests(NotificationsConfigMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_besluittype_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("besluittype_create")

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "zaaktypen": [],
            "omschrijving": "test",
            "omschrijvingGeneriek": "",
            "besluitcategorie": "",
            "reactietermijn": "P14D",
            "publicatieIndicatie": True,
            "publicatietekst": "",
            "publicatietermijn": None,
            "toelichting": "",
            "informatieobjecttypen": [],
            "beginGeldigheid": "2019-01-01",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "besluittypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "besluittype",
            "resourceUrl": data["url"],
        }

        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluittype_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):

        besluittype = BesluitTypeFactory.create()
        url = reverse(besluittype)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "besluittypen",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
            },
            "resource": "besluittype",
            "resourceUrl": f"http://testserver{url}",
        }
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_informatieobjecttype_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("informatieobjecttype_create")

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
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
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_informatieobjecttype_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):

        iotype = InformatieObjectTypeFactory.create()
        url = reverse(iotype)

        # 1. check that notification task is called
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
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaaktype_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("zaaktype_create")

        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "zaaktypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "zaaktype",
            "resourceUrl": data["url"],
        }
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaaktype_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        zaaktype = ZaakTypeFactory.create()
        url = reverse(zaaktype)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "zaaktypen",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
            },
            "resource": "zaaktype",
            "resourceUrl": f"http://testserver{url}",
        }
        mock_notif.assert_called_with(message)

        # 2. check that if task is failed, DB object is created for failed notification
        mock_nrc_oas_get(m)
        mock_notification_send(m, status_code=403)

        with self.assertRaises(NotificationException):
            send_notification(message)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
