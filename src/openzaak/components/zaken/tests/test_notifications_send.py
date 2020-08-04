# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os
from unittest.mock import patch

from django.test import override_settings
from django.utils.timezone import now

from django_db_logger.models import StatusLog
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.notifications.models import NotificationsConfig
from vng_api_common.tests import reverse

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
from openzaak.notifications.tests.mixins import NotificationServiceMixin
from openzaak.utils.tests import JWTAuthMixin

from ..models import Zaak
from .factories import (
    ResultaatFactory,
    RolFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
class SendNotifTestCase(NotificationServiceMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch("zds_client.Client.from_url")
    def test_send_notif_create_zaak(self, mock_client):
        """
        Check if notifications will be send when zaak is created
        """
        client = mock_client.return_value
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
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
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )

    @patch("zds_client.Client.from_url")
    def test_send_notif_delete_resultaat(self, mock_client):
        """
        Check if notifications will be send when resultaat is deleted
        """
        client = mock_client.return_value
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        zaaktype_url = reverse(zaak.zaaktype)
        resultaat = ResultaatFactory.create(zaak=zaak)
        resultaat_url = get_operation_url("resultaat_update", uuid=resultaat.uuid)

        response = self.client.delete(resultaat_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        client.create.assert_called_once_with(
            "notificaties",
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
                    "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                },
            },
        )


@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationServiceMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_zaak_create_fail_send_notification_create_db_entry(self):
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": data["bronorganisatie"],
                "zaaktype": f"http://testserver{zaaktype_url}",
                "vertrouwelijkheidaanduiding": data["vertrouwelijkheidaanduiding"],
            },
            "resource": "zaak",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaak_delete_fail_send_notification_create_db_entry(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaak",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_status_create_fail_send_notification_create_db_entry(self):
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
            "resource": "status",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaakobject_create_fail_send_notification_create_db_entry(self):
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
            "resource": "zaakobject",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaakinformatieobject_create_fail_send_notification_create_db_entry(self):
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
        zio = ZaakInformatieObjectFactory.create()
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

    def test_zaakeigenschap_create_fail_send_notification_create_db_entry(self):
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
            "resource": "zaakeigenschap",
            "resourceUrl": data["url"],
        }
        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_klantcontact_create_fail_send_notification_create_db_entry(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        url = get_operation_url("klantcontact_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "datumtijd": "2019-01-01T12:00:00Z",
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
            "resource": "klantcontact",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_rol_create_fail_send_notification_create_db_entry(self):
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
            "resource": "rol",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_rol_delete_fail_send_notification_create_db_entry(self):
        rol = RolFactory.create()
        url = reverse(rol)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(rol.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": rol.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(rol.zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": rol.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "rol",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_resultaat_create_fail_send_notification_create_db_entry(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        resultaattype_url = reverse(resultaattype)

        url = get_operation_url("resultaat_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "resultaattype": f"http://testserver{resultaattype_url}",
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
            "resource": "resultaat",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_resultaat_delete_fail_send_notification_create_db_entry(self):
        resultaat = ResultaatFactory.create()
        url = reverse(resultaat)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(resultaat.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": resultaat.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(resultaat.zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": resultaat.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "resultaat",
            "resourceUrl": f"http://testserver{url}",
        }
        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)

    def test_zaakbesluit_create_fail_send_notification_create_db_entry(self):
        besluit = BesluitFactory.create(for_zaak=True)
        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": besluit.zaak.uuid})

        response = self.client.post(
            url, data={"besluit": f"http://testserver{besluit_url}",}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(StatusLog.objects.count(), 1)

        logged_warning = StatusLog.objects.get()
        failed = FailedNotification.objects.get()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(besluit.zaak)}",
            "kanaal": "zaken",
            "kenmerken": {
                "bronorganisatie": besluit.zaak.bronorganisatie,
                "zaaktype": f"http://testserver{reverse(besluit.zaak.zaaktype)}",
                "vertrouwelijkheidaanduiding": besluit.zaak.vertrouwelijkheidaanduiding,
            },
            "resource": "zaakbesluit",
            "resourceUrl": data["url"],
        }

        self.assertEqual(failed.statuslog_ptr, logged_warning)
        self.assertEqual(failed.message, message)


@override_settings(NOTIFICATIONS_DISABLED=False, CMIS_ENABLED=False)
class InvalidNotifConfigTests(
    NotificationServiceMixin, JWTAuthMixin, APITransactionTestCase
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

    def test_invalid_notification_config_create(self):
        conf = NotificationsConfig.get_solo()
        conf.api_root = "bla"
        conf.save()

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
        self.assertFalse(StatusLog.objects.exists())

    def test_notification_config_inaccessible_create(self):
        conf = NotificationsConfig.get_solo()
        conf.api_root = "http://localhost:8001/api/v1/"
        conf.save()

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
        self.assertFalse(StatusLog.objects.exists())
