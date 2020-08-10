# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import json

from django.contrib.sites.models import Site
from django.test import override_settings, tag

from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from .factories import BesluitInformatieObjectFactory
from .utils import get_operation_url


@tag("cmis")
@freeze_time("2018-09-07T00:00:00Z")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=True)
class SendNotifTestCase(
    NotificationServiceMixin, JWTAuthMixin, APICMISTestCase, OioMixin
):

    heeft_alle_autorisaties = True

    def test_send_notif_delete_besluitinformatieobject(self):
        """
        Check if notifications will be send when besluitinformatieobject is deleted
        """
        # client = mock_client.return_value
        # besluit = BesluitFactory.create()
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        besluittype_url = reverse(besluit.besluittype)
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        bio = BesluitInformatieObjectFactory.create(
            besluit=besluit, informatieobject=eio_url
        )
        bio_url = get_operation_url("besluitinformatieobject_delete", uuid=bio.uuid)

        response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        notificaties_requests = []
        for request in self.adapter.request_history:
            if request.path == "/api/v1/notificaties":
                notificaties_requests.append(request)

        self.assertEqual(len(notificaties_requests), 1)
        notificatie_request = json.loads(notificaties_requests[0].text)

        expected_data = {
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
        }

        for key, value in expected_data.items():
            self.assertIn(key, notificatie_request)
            self.assertEqual(value, notificatie_request[key])


@tag("cmis")
@freeze_time("2019-01-01T12:00:00Z")
@override_settings(
    NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS, CMIS_ENABLED=True
)
class FailedNotificationCMISTests(
    NotificationServiceMixin, JWTAuthMixin, APICMISTestCase, OioMixin
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
        self,
    ):
        url = get_operation_url("besluitinformatieobject_create")

        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit)
        data = {
            "informatieobject": io_url,
            "besluit": f"http://testserver{besluit_url}",
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
        self,
    ):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=eio_url, besluit=besluit
        )
        url = reverse(bio)

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
