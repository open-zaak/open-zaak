# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os
from unittest import skip
from unittest.mock import patch

from django.test import override_settings, tag
from django.utils.timezone import now

import requests_mock
from django_db_logger.models import StatusLog
from freezegun import freeze_time
from notifications_api_common.models import NotificationsConfig
from notifications_api_common.tasks import NotificationException, send_notification
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.models import FailedNotification
from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import Zaak
from .factories import (
    ResultaatFactory,
    RolFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import (
    ZAAK_WRITE_KWARGS,
    get_catalogus_response,
    get_operation_url,
    get_zaaktype_response,
)

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("notifications")
@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class SendNotifTestCase(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_send_notif_create_zaak(self, mock_notif):
        """
        Check if notifications will be send when zaak is created
        """
        url = get_operation_url("zaak_create")
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        catalogus_url = reverse(zaaktype.catalogus)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": data["url"],
                "resource": "zaak",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": "517439943",
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "zaaktype.catalogus": f"http://testserver{catalogus_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_send_notif_create_zaak_external_zaaktype(self, mock_notif):
        """
        Check if the zaaktype.catalogus kenmerk is correctly sent if the Zaak
        has an external zaaktype
        """
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        url = get_operation_url("zaak_create")
        zaaktype_url = "https://externe.catalogus.nl/api/v1/zaaktypen/1"
        catalogus_url = "https://externe.catalogus.nl/api/v1/catalogi/1"
        data = {
            "zaaktype": zaaktype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            with requests_mock.Mocker() as m:
                mock_ztc_oas_get(m)
                m.get(
                    zaaktype_url,
                    json=get_zaaktype_response(catalogus_url, zaaktype_url),
                )
                m.get(
                    catalogus_url,
                    json=get_catalogus_response(catalogus_url, zaaktype_url),
                )

                response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": data["url"],
                "resource": "zaak",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": "517439943",
                    "zaaktype": zaaktype_url,
                    "zaaktype.catalogus": catalogus_url,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_send_notif_create_zaak_external_zaaktype_failed_to_fetch_catalogus(
        self, mock_notif
    ):
        """
        Check if the zaaktype.catalogus kenmerk is left empty sent if the Zaak
        has an external zaaktype and the Catalogus could not be fetched
        """
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        url = get_operation_url("zaak_create")
        zaaktype_url = "https://externe.catalogus.nl/api/v1/zaaktypen/1"
        catalogus_url = "https://externe.catalogus.nl/api/v1/catalogi/1"
        data = {
            "zaaktype": zaaktype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            with requests_mock.Mocker() as m:
                mock_ztc_oas_get(m)
                m.get(
                    zaaktype_url,
                    json=get_zaaktype_response(catalogus_url, zaaktype_url),
                )
                m.get(
                    catalogus_url,
                    # json=get_catalogus_response(catalogus_url, zaaktype_url),
                    exc=RequestException,
                )

                response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": data["url"],
                "resource": "zaak",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": "517439943",
                    "zaaktype": zaaktype_url,
                    "zaaktype.catalogus": "",  # could not be fetched
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )

    def test_send_notif_delete_resultaat(self, mock_notif):
        """
        Check if notifications will be send when resultaat is deleted
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaaktype_url = reverse(zaak.zaaktype)
        resultaat = ResultaatFactory.create(zaak=zaak)
        resultaat_url = get_operation_url("resultaat_update", uuid=resultaat.uuid)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(resultaat_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": f"http://testserver{zaak_url}",
                "resource": "resultaat",
                "resourceUrl": f"http://testserver{resultaat_url}",
                "actie": "destroy",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": zaak.bronorganisatie,
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                    "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                },
            },
        )

    def test_send_notif_update_zaakobject(self, mock_notif):
        """
        Check if notifications will be send when zaakobject is updated
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaakobject = ZaakObjectFactory.create(zaak=zaak, relatieomschrijving="old")
        zaakobject_url = get_operation_url("zaakobject_update", uuid=zaakobject.uuid)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(zaakobject_url, {"relatieomschrijving": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": f"http://testserver{zaak_url}",
                "resource": "zaakobject",
                "resourceUrl": f"http://testserver{zaakobject_url}",
                "actie": "partial_update",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": zaak.bronorganisatie,
                    "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                    "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                    "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                },
            },
        )

    def test_send_notif_update_zaak_eigenschap(self, mock_notif):
        """
        Check if notifications will be send when zaak-eigenschap is updated
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaakeigenschap = ZaakEigenschapFactory.create(zaak=zaak, waarde="old")
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_update", uuid=zaakeigenschap.uuid, zaak_uuid=zaak.uuid
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(zaakeigenschap_url, data={"waarde": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_notif.assert_called_once_with(
            {
                "kanaal": "zaken",
                "hoofdObject": f"http://testserver{zaak_url}",
                "resource": "zaakeigenschap",
                "resourceUrl": f"http://testserver{zaakeigenschap_url}",
                "actie": "partial_update",
                "aanmaakdatum": "2012-01-14T00:00:00Z",
                "kenmerken": {
                    "bronorganisatie": zaak.bronorganisatie,
                    "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                    "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                    "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                },
            },
        )


@tag("notifications", "DEPRECATED")
@requests_mock.Mocker()
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
@patch("notifications_api_common.viewsets.send_notification.delay")
class FailedNotificationTests(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_zaak_create_fail_send_notification_create_db_entry(self, m, mock_notif):
        url = get_operation_url("zaak_create")
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": data["bronorganisatie"],
                "zaaktype": f"http://testserver{zaaktype_url}",
                "zaaktype.catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": data["vertrouwelijkheidaanduiding"],
            },
            "resource": "zaak",
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

    def test_zaak_delete_fail_send_notification_create_db_entry(self, m, mock_notif):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaak",
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

    def test_status_create_fail_send_notification_create_db_entry(self, m, mock_notif):
        url = get_operation_url("status_create")
        zaak = ZaakFactory.create(
            einddatum=now(),
            archiefactiedatum="2020-01-01",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
        )
        zaak_url = reverse(zaak)
        ResultaatFactory.create(
            zaak=zaak,
            resultaattype__brondatum_archiefprocedure_afleidingswijze=Afleidingswijze.ander_datumkenmerk,
        )
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": "2019-01-01T12:00:00Z",
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
            "resource": "status",
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

    def test_zaakobject_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        data = {
            "zaak": zaak_url,
            "objectType": "buurt",
            "objectIdentificatie": {
                "buurtCode": "aa",
                "buurtNaam": "bb",
                "gemGemeenteCode": "cc",
                "wykWijkCode": "dd",
            },
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
            "resource": "zaakobject",
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

    def test_zaakinformatieobject_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        url = get_operation_url("zaakinformatieobject_create")

        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )
        zaak_url = reverse(zaak)
        io_url = reverse(io)
        data = {
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
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

    @skip(reason="Standard does not prescribe ZIO destroy notifications.")
    def test_zaakinformatieobject_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        zio = ZaakInformatieObjectFactory.create()
        url = reverse(zio)

        # this endpoint does not run in a transaction.atomic() block, so the
        # self.captureOnCommitCallbacks context manager is not useful
        # 1. check that notification task is called
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
                "zaaktype.catalogus": f"http://testserver{reverse(zio.zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": zio.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakinformatieobject",
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

    def test_zaakeigenschap_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak.uuid)
        eigenschap = EigenschapFactory.create(zaaktype=zaak.zaaktype)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "ja",
        }

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
            "resource": "zaakeigenschap",
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

    def test_klantcontact_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        url = get_operation_url("klantcontact_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "datumtijd": "2019-01-01T12:00:00Z",
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
            "resource": "klantcontact",
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

    def test_rol_create_fail_send_notification_create_db_entry(self, m, mock_notif):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)

        url = get_operation_url("rol_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkeneType": "medewerker",
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "nee",
            "betrokkeneIdentificatie": {
                "identificatie": "1111",
                "achternaam": "a",
                "voorletters": "a",
                "voorvoegselAchternaam": "a",
            },
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
            "resource": "rol",
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

    def test_rol_delete_fail_send_notification_create_db_entry(self, m, mock_notif):
        rol = RolFactory.create()
        url = reverse(rol)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(rol.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": rol.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(rol.zaak.zaaktype)}",
                "zaaktype.catalogus": f"http://testserver{reverse(rol.zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": rol.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "rol",
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

    def test_resultaat_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        resultaattype_url = reverse(resultaattype)

        url = get_operation_url("resultaat_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "resultaattype": f"http://testserver{resultaattype_url}",
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
            "resource": "resultaat",
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

    def test_resultaat_delete_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        resultaat = ResultaatFactory.create()
        url = reverse(resultaat)

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(resultaat.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": resultaat.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(resultaat.zaak.zaaktype)}",
                "zaaktype.catalogus": f"http://testserver{reverse(resultaat.zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": resultaat.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "resultaat",
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

    def test_zaakbesluit_create_fail_send_notification_create_db_entry(
        self, m, mock_notif
    ):
        besluit = BesluitFactory.create(for_zaak=True)
        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": besluit.zaak.uuid})

        # 1. check that notification task is called
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url, data={"besluit": f"http://testserver{besluit_url}"}
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(besluit.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": besluit.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(besluit.zaak.zaaktype)}",
                "zaaktype.catalogus": f"http://testserver{reverse(besluit.zaak.zaaktype.catalogus)}",
                "vertrouwelijkheidaanduiding": besluit.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakbesluit",
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


@tag("notifications")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class InvalidNotifConfigTests(
    NotificationsConfigMixin, JWTAuthMixin, APITransactionTestCase
):

    client_id = "test"
    secret = "test"
    heeft_alle_autorisaties = True

    def setUp(self):
        JWTSecret.objects.get_or_create(
            identifier=self.client_id, defaults={"secret": self.secret}
        )

        self.applicatie = Applicatie.objects.create(
            client_ids=[self.client_id],
            label="for test",
            heeft_alle_autorisaties=self.heeft_alle_autorisaties,
        )

        super().setUp()

        # In dev mode, the exception handler checks if it needs to transform the
        # exception into a 500 response, or raise it so it can be debugged/is obvious
        # there is a bug. This however breaks tests relying on the exception-catching.
        # The behaviour is in :func:`vng_api_common.views.exception_handler` - and can
        # be enabled/disabled with an envvar. Here, we enforce production-mode responses.
        if "DEBUG" in os.environ:
            prev_debug_value = os.environ["DEBUG"]

            def _reset_debug():
                os.environ["DEBUG"] = prev_debug_value

            os.environ["DEBUG"] = "no"
            self.addCleanup(_reset_debug)

    # TODO APIClient doesnt seem to complain about base_url `bla/`
    # def test_invalid_notification_config_create(self, mock_notif):
    #     self._configure_notifications("bla")

    #     url = get_operation_url("zaak_create")
    #     zaaktype = ZaakTypeFactory.create(concept=False)
    #     zaaktype_url = reverse(zaaktype)
    #     data = {
    #         "zaaktype": f"http://testserver{zaaktype_url}",
    #         "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
    #         "bronorganisatie": "517439943",
    #         "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
    #         "registratiedatum": "2012-01-13",
    #         "startdatum": "2012-01-13",
    #         "toelichting": "Een stel dronken toeristen speelt versterkte "
    #         "muziek af vanuit een gehuurde boot.",
    #         "zaakgeometrie": {
    #             "type": "Point",
    #             "coordinates": [4.910649523925713, 52.37240093589432],
    #         },
    #     }

    #     response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

    #     self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    #     self.assertFalse(Zaak.objects.exists())
    #     mock_notif.assert_not_called()

    @override_settings(SOLO_CACHE=None)
    def test_notification_config_inaccessible_create(self, mock_notif):
        self._configure_notifications("http://localhost:8001/api/v1/")
        # delete the service, so no client can be built
        NotificationsConfig.get_solo().notifications_api_service.delete()

        url = get_operation_url("zaak_create")
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2012-01-13",
            "startdatum": "2012-01-13",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(Zaak.objects.exists())
        mock_notif.assert_not_called()
