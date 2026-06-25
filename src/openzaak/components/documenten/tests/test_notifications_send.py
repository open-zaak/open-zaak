# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import base64
import uuid
from unittest.mock import call, patch

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import FailedNotification, NotificationResponse
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin
from openzaak.tests.utils.urls import reverse

from ...zaken.tests.factories import StatusFactory, ZaakFactory
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory
from .utils import get_operation_url


@tag("notifications")
@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
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
            None,
        )

    @tag("convenience-endpoints")
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

        url = get_operation_url("registreerdocument_create")

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
                    },
                    None,
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
                    },
                    None,
                ),
            ],
            any_order=True,
        )


@tag("notifications")
@temp_private_root()
@requests_mock.Mocker()
@override_settings(
    NOTIFICATIONS_DISABLED=False,
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_eio_create_fail_send_notification_create_db_entry(self, m):
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

        mock_notification_send(m, status_code=403)

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

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_eio_delete_fail_send_notification_create_db_entry(self, m):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)

        mock_notification_send(m, status_code=403)

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

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_gebruiksrechten_create_fail_send_notification_create_db_entry(self, m):
        url = get_operation_url("gebruiksrechten_create")

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)
        data = {
            "informatieobject": f"http://testserver{eio_url}",
            "startdatum": "2018-12-24T00:00:00Z",
            "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
        }

        mock_notification_send(m, status_code=403)

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

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_gebruiksrechten_delete_fail_send_notification_create_db_entry(self, m):
        gebruiksrechten = GebruiksrechtenFactory.create()

        url = reverse(gebruiksrechten)

        mock_notification_send(m, status_code=403)

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

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)
