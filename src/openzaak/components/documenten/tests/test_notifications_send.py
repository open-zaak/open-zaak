# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import base64
import uuid
from unittest.mock import call, patch

from django.test import override_settings, tag

import requests_mock
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from notifications_api_common.tasks import NotificationException, send_notification
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.notifications.tests.utils import LOGGING_SETTINGS
from openzaak.tests.utils import JWTAuthMixin

from ...zaken.tests.factories import StatusFactory, ZaakFactory
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory
from .utils import get_operation_url


@tag("notifications")
@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class SendNotifTestCase(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_send_notif_create_enkelvoudiginformatieobject(self, mock_notif):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
            "identificatie": "AMS20180701001",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "text_extra.txt",
            "auteur": "ANONIEM",
            "formaat": "text/plain",
            "taal": "dut",
            "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        mock_notif.assert_called_once_with(
            {
                "kanaal": "documenten",
                "hoofdObject": data["url"],
                "resource": "enkelvoudiginformatieobject",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": "159351741",
                    "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                    "informatieobjecttype.catalogus": f"http://testserver{reverse(informatieobjecttype.catalogus)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )

    def test_send_notif_register_document(self, mock_notif):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=informatieobjecttype
        )

        _status = StatusFactory.create(zaak=zaak)
        status_url = reverse(_status)

        url = reverse("registereddocument-list")

        data = {
            "enkelvoudiginformatieobject": {
                "identificatie": "AMS20180701001",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-07-01",
                "titel": "text_extra.txt",
                "auteur": "ANONIEM",
                "formaat": "text/plain",
                "taal": "dut",
                "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            "zaakinformatieobject": {
                "zaak": f"http://testserver{zaak_url}",
                "titel": "string",
                "beschrijving": "string",
                "vernietigingsdatum": "2019-08-24T14:15:22Z",
                "status": f"http://testserver{status_url}",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(mock_notif.call_count, 2)
        mock_notif.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "documenten",
                        "hoofdObject": data["enkelvoudiginformatieobject"]["url"],
                        "resource": "enkelvoudiginformatieobject",
                        "resourceUrl": data["enkelvoudiginformatieobject"]["url"],
                        "actie": "create",
                        "aanmaakdatum": "2012-01-14T00:00:00Z",
                        "kenmerken": {
                            "bronorganisatie": "159351741",
                            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                            "informatieobjecttype.catalogus": f"http://testserver{reverse(informatieobjecttype.catalogus)}",
                            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                        },
                    }
                ),
                call(
                    {
                        "kanaal": "zaken",
                        "hoofdObject": data["zaakinformatieobject"]["zaak"],
                        "resource": "zaakinformatieobject",
                        "resourceUrl": data["zaakinformatieobject"]["url"],
                        "actie": "create",
                        "aanmaakdatum": "2012-01-14T00:00:00Z",
                        "kenmerken": {
                            "bronorganisatie": zaak.bronorganisatie,
                            "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                            "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                        },
                    }
                ),
            ],
            any_order=True,
        )


@tag("notifications", "DEPRECATED")
@requests_mock.Mocker()
@override_settings(NOTIFICATIONS_DISABLED=False, LOGGING=LOGGING_SETTINGS)
@freeze_time("2019-01-01T12:00:00Z")
@patch("notifications_api_common.viewsets.send_notification.delay")
class FailedNotificationTests(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_eio_create_fail_send_notification_create_db_entry(self, m, mock_notif):
        url = get_operation_url("enkelvoudiginformatieobject_create")

        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": base64.b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
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
            "kanaal": "documenten",
            "kenmerken": {
                "bronorganisatie": "159351741",
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                "informatieobjecttype.catalogus": f"http://testserver{reverse(informatieobjecttype.catalogus)}",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
            "resource": "enkelvoudiginformatieobject",
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

    def test_eio_delete_fail_send_notification_create_db_entry(self, m, mock_notif):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "documenten",
            "kenmerken": {
                "bronorganisatie": eio.bronorganisatie,
                "informatieobjecttype": f"http://testserver{reverse(eio.informatieobjecttype)}",
                "informatieobjecttype.catalogus": f"http://testserver{reverse(eio.informatieobjecttype.catalogus)}",
                "vertrouwelijkheidaanduiding": eio.vertrouwelijkheidaanduiding,
            },
            "resource": "enkelvoudiginformatieobject",
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

    def test_gebruiksrechten_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("gebruiksrechten_create")

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)
        data = {
            "informatieobject": f"http://testserver{eio_url}",
            "startdatum": "2018-12-24T00:00:00Z",
            "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{eio_url}",
            "kanaal": "documenten",
            "kenmerken": {
                "bronorganisatie": eio.bronorganisatie,
                "informatieobjecttype": f"http://testserver{reverse(eio.informatieobjecttype)}",
                "informatieobjecttype.catalogus": f"http://testserver{reverse(eio.informatieobjecttype.catalogus)}",
                "vertrouwelijkheidaanduiding": eio.vertrouwelijkheidaanduiding,
            },
            "resource": "gebruiksrechten",
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

    def test_gebruiksrechten_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        gebruiksrechten = GebruiksrechtenFactory.create()

        url = reverse(gebruiksrechten)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        eio = EnkelvoudigInformatieObject.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(eio)}",
            "kanaal": "documenten",
            "kenmerken": {
                "bronorganisatie": eio.bronorganisatie,
                "informatieobjecttype": f"http://testserver{reverse(eio.informatieobjecttype)}",
                "informatieobjecttype.catalogus": f"http://testserver{reverse(eio.informatieobjecttype.catalogus)}",
                "vertrouwelijkheidaanduiding": eio.vertrouwelijkheidaanduiding,
            },
            "resource": "gebruiksrechten",
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
