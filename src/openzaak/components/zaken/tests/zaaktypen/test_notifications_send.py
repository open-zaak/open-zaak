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

from openzaak.components.catalogi.constants import AardRelatieChoices, InternExtern
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.catalogi.tests.base import APITestCase
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ZaakTypeFactory,
)
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.utils.urls import reverse


@tag("notifications")
@freeze_time("2018-09-07T00:00:00Z")
@temp_private_root()
@override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class ZaakTypeSendNotifTestCase(NotificationsConfigMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    NAMESPACE = "zaken"
    CATALOGUS_NAMESPACE = "zaken"

    def _expected_message(self, zaaktype, actie: str) -> dict:
        return {
            "kanaal": "zaaktypen",
            "hoofdObject": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
            "resource": "zaaktype",
            "resourceUrl": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
            "actie": actie,
            "aanmaakdatum": "2018-09-07T00:00:00Z",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(zaaktype.catalogus, namespace='zaken')}",
            },
        }

    def test_send_notif_create_zaaktype(self, mock_notif):
        catalogus = CatalogusFactory.create()
        catalogus_url = reverse(catalogus, namespace=self.CATALOGUS_NAMESPACE)
        url = reverse(ZaakType, namespace=self.NAMESPACE)

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
            "gerelateerdeZaaktypen": [],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{catalogus_url}",
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaaktype = ZaakType.objects.get()
        self.assertEqual(
            response.json()["url"],
            f"http://testserver{reverse(zaaktype, namespace=self.NAMESPACE)}",
        )
        mock_notif.assert_has_calls(
            [call(self._expected_message(zaaktype, "create"), None)]
        )

    def test_send_notif_update_zaaktype(self, mock_notif):
        zaaktype = ZaakTypeFactory.create(concept=True)
        url = reverse(zaaktype, namespace=self.NAMESPACE)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {"omschrijving": "Blabla"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["url"],
            f"http://testserver{reverse(zaaktype, namespace=self.NAMESPACE)}",
        )
        mock_notif.assert_has_calls(
            [call(self._expected_message(zaaktype, "partial_update"), None)]
        )

    def test_send_notif_delete_zaaktype(self, mock_notif):
        zaaktype = ZaakTypeFactory.create(concept=True)
        url = reverse(zaaktype, namespace=self.NAMESPACE)
        expected = self._expected_message(zaaktype, "destroy")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        mock_notif.assert_has_calls([call(expected, None)])


@tag("notifications")
@requests_mock.Mocker()
@override_settings(
    NOTIFICATIONS_DISABLED=False,
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2019-01-01T12:00:00Z")
class ZaakTypeFailedNotificationTests(NotificationsConfigMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    NAMESPACE = "zaken"

    def test_zaaktype_create_fail_send_notification_create_db_entry(self, m):
        url = reverse(ZaakType, namespace=self.NAMESPACE)

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

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaaktype = ZaakType.objects.first()
        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
            "kanaal": "zaaktypen",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(zaaktype.catalogus, namespace='zaken')}",
            },
            "resource": "zaaktype",
            "resourceUrl": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_zaaktype_delete_fail_send_notification_create_db_entry(self, m):
        zaaktype = ZaakTypeFactory.create()
        url = reverse(zaaktype, namespace=self.NAMESPACE)

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
            "kanaal": "zaaktypen",
            "kenmerken": {
                "catalogus": f"http://testserver{reverse(zaaktype.catalogus, namespace='zaken')}",
            },
            "resource": "zaaktype",
            "resourceUrl": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)
