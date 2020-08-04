# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS

from ..constants import AardRelatieChoices, InternExtern
from .base import APITestCase
from .factories import BesluitTypeFactory, InformatieObjectTypeFactory, ZaakTypeFactory
from .utils import get_operation_url


@override_settings(NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationServiceMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_besluittype_create_fail_send_notification_create_db_entry(self):
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
            "kanaal": "besluittypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "besluittype",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_besluittype_delete_fail_send_notification_create_db_entry(self):
        besluittype = BesluitTypeFactory.create()
        url = reverse(besluittype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
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

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_informatieobjecttype_create_fail_send_notification_create_db_entry(self):
        url = get_operation_url("informatieobjecttype_create")

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
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
            "kanaal": "informatieobjecttypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "informatieobjecttype",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_informatieobjecttype_delete_fail_send_notification_create_db_entry(self):
        iotype = InformatieObjectTypeFactory.create()
        url = reverse(iotype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
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

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaaktype_create_fail_send_notification_create_db_entry(self):
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
            "kanaal": "zaaktypen",
            "kenmerken": {
                "catalogus": f"http://testserver{self.catalogus_detail_url}",
            },
            "resource": "zaaktype",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaaktype_delete_fail_send_notification_create_db_entry(self):
        zaaktype = ZaakTypeFactory.create()
        url = reverse(zaaktype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
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

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
