import base64
import uuid
from unittest.mock import patch

from django.test import override_settings
from django.utils.timezone import datetime, make_aware

from djangorestframework_camel_case.util import camelize
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.notificaties.models import FailedNotification
from openzaak.utils.tests import JWTAuthMixin, LoggingMixin

from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory
from .utils import get_operation_url


@freeze_time("2012-01-14")
@override_settings(NOTIFICATIONS_DISABLED=False)
class SendNotifTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @patch("zds_client.Client.from_url")
    def test_send_notif_create_enkelvoudiginformatieobject(self, mock_client):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        client = mock_client.return_value
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

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        client.create.assert_called_once_with(
            "notificaties",
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
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
            },
        )


@override_settings(NOTIFICATIONS_DISABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(LoggingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_eio_create_fail_send_notification_create_db_entry(self):
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

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "documenten")
        self.assertEqual(failed.model, "EnkelvoudigInformatieObject")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_eio_delete_fail_send_notification_create_db_entry(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "documenten")
        self.assertEqual(failed.model, "EnkelvoudigInformatieObject")
        self.assertEqual(failed.instance, failed.data)

    def test_gebruiksrechten_create_fail_send_notification_create_db_entry(self):
        url = get_operation_url("gebruiksrechten_create")

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)
        data = {
            "informatieobject": f"http://testserver{eio_url}",
            "startdatum": "2018-12-24T00:00:00Z",
            "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "documenten")
        self.assertEqual(failed.model, "Gebruiksrechten")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_gebruiksrechten_delete_fail_send_notification_create_db_entry(self):
        gebruiksrechten = GebruiksrechtenFactory.create()
        url = reverse(gebruiksrechten)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "documenten")
        self.assertEqual(failed.model, "Gebruiksrechten")
        self.assertEqual(failed.instance, failed.data)
