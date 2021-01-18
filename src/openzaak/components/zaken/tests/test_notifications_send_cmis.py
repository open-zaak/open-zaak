# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from .factories import ZaakInformatieObjectFactory
from .utils import get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("cmis")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=True)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationCMISTests(
    NotificationServiceMixin, JWTAuthMixin, APICMISTestCase, OioMixin
):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_zaakinformatieobject_create_fail_send_notification_create_db_entry(self):
        site = Site.objects.get_current()
        url = get_operation_url("zaakinformatieobject_create")

        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )
        zaak_url = reverse(zaak)
        data = {
            "informatieobject": io_url,
            "zaak": f"http://{site.domain}{zaak_url}",
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
            "hoofdObject": f"http://testserver{zaak_url}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakinformatieobject",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaakinformatieobject_delete_fail_send_notification_create_db_entry(self):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        self.create_zaak_besluit_services()
        zio = ZaakInformatieObjectFactory.create(
            informatieobject=io_url, zaak=self.create_zaak()
        )
        url = reverse(zio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
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

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)
