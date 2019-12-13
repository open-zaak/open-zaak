from datetime import datetime
from unittest.mock import patch

from django.test import override_settings
from django.utils.timezone import datetime, make_aware, now

from djangorestframework_camel_case.util import camelize
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    VertrouwelijkheidsAanduiding,
)
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
from openzaak.notificaties.models import FailedNotification
from openzaak.utils.tests import JWTAuthMixin, LoggingMixin

from .factories import (
    ResultaatFactory,
    RolFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(JWTAuthMixin, APITestCase):
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


@override_settings(NOTIFICATIONS_DISABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(LoggingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Zaak")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_zaak_delete_fail_send_notification_create_db_entry(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Zaak")
        self.assertEqual(failed.instance, failed.data)

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
            "zaak": zaak_url,
            "statustype": statustype_url,
            "datumStatusGezet": "2019-01-01T12:00:00Z",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Status")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_zaakobject_create_fail_send_notification_create_db_entry(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create(
            einddatum=now(),
            archiefactiedatum="2020-01-01",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
        )
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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "ZaakObject")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_zaakinformatieobject_create_fail_send_notification_create_db_entry(self,):
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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "ZaakInformatieObject")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_zaakinformatieobject_delete_fail_send_notification_create_db_entry(self,):
        zio = ZaakInformatieObjectFactory.create()
        url = reverse(zio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "ZaakInformatieObject")
        self.assertEqual(failed.instance, failed.data)

    def test_zaakeigenschap_create_fail_send_notification_create_db_entry(self,):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak.uuid)
        eigenschap = EigenschapFactory.create(zaaktype=zaak.zaaktype)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "eigenschap": eigenschap_url,
            "waarde": "ja",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "ZaakEigenschap")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_klantcontact_create_fail_send_notification_create_db_entry(self,):
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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "KlantContact")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_rol_create_fail_send_notification_create_db_entry(self,):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)

        url = get_operation_url("rol_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkeneType": "medewerker",
            "roltype": roltype_url,
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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Rol")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_rol_delete_fail_send_notification_create_db_entry(self,):
        rol = RolFactory.create()
        url = reverse(rol)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Rol")
        self.assertEqual(failed.instance, failed.data)

    def test_resultaat_create_fail_send_notification_create_db_entry(self,):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        resultaattype_url = reverse(resultaattype)

        url = get_operation_url("resultaat_create")
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "resultaattype": resultaattype_url,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Resultaat")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_resultaat_delete_fail_send_notification_create_db_entry(self,):
        resultaat = ResultaatFactory.create()
        url = reverse(resultaat)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "Resultaat")
        self.assertEqual(failed.instance, failed.data)

    def test_resultaat_create_fail_send_notification_create_db_entry(self,):
        besluit = BesluitFactory.create(for_zaak=True)
        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": besluit.zaak.uuid})

        response = self.client.post(url, {"besluit": besluit_url})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "zaken")
        self.assertEqual(failed.model, "ZaakBesluit")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)
