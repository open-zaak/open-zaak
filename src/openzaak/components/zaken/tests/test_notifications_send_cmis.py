# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest import skip
from unittest.mock import patch

from django.contrib.sites.models import Site
from django.test import override_settings, tag

import requests_mock
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from notifications_api_common.tasks import NotificationException, send_notification
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from .factories import ZaakFactory, ZaakInformatieObjectFactory
from .utils import get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("notifications", "DEPRECATED")
@requests_mock.Mocker(real_http=True)  # for CMIS requests
@require_cmis
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=True)
@freeze_time("2019-01-01T12:00:00Z")
@patch("notifications_api_common.viewsets.send_notification.delay")
class FailedNotificationCMISTests(
    NotificationsConfigMixin, JWTAuthMixin, APICMISTestCase
):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_zaakinformatieobject_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        site = Site.objects.get_current()
        url = get_operation_url("zaakinformatieobject_create")

        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )

        data = {
            "informatieobject": io_url,
            "zaak": f"http://{site.domain}{zaak_url}",
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{zaak_url}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakinformatieobject",
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

    @skip(reason="Standard does not prescribe ZIO destroy notifications.")
    def test_zaakinformatieobject_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://testserver{reverse(io)}"

        zio = ZaakInformatieObjectFactory.create(informatieobject=io_url)
        url = reverse(zio)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(zio.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": zio.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(zio.zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": zio.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakinformatieobject",
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
