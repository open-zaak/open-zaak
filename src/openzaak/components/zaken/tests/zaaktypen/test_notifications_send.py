# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import FailedNotification, NotificationResponse
from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.constants import AardRelatieChoices, InternExtern
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.catalogi.tests.base import APITestCase
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.utils.urls import reverse


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
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
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
                "catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
            },
            "resource": "zaaktype",
            "resourceUrl": f"http://testserver{reverse(zaaktype, namespace='zaken')}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)
