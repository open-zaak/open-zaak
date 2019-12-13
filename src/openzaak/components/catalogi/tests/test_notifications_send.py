from unittest.mock import patch

from django.test import override_settings
from django.utils.timezone import datetime, make_aware

from djangorestframework_camel_case.util import camelize
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.notificaties.models import FailedNotification
from openzaak.utils.tests import LoggingMixin

from ..constants import AardRelatieChoices, InternExtern
from .base import APITestCase
from .factories import BesluitTypeFactory, InformatieObjectTypeFactory, ZaakTypeFactory
from .utils import get_operation_url


@override_settings(NOTIFICATIONS_DISABLED=False)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(LoggingMixin, APITestCase):
    heeft_alle_autorisaties = True

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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "BesluitType")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_besluittype_delete_fail_send_notification_create_db_entry(self):
        besluittype = BesluitTypeFactory.create()
        url = reverse(besluittype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "BesluitType")
        self.assertEqual(failed.instance, failed.data)

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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "InformatieObjectType")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_informatieobjecttype_delete_fail_send_notification_create_db_entry(self):
        iotype = InformatieObjectTypeFactory.create()
        url = reverse(iotype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "InformatieObjectType")
        self.assertEqual(failed.instance, failed.data)

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

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 201)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "ZaakType")
        self.assertDictEqual(camelize(failed.data), data)
        self.assertEqual(failed.instance, None)

    def test_zaaktype_delete_fail_send_notification_create_db_entry(self):
        iotype = ZaakTypeFactory.create()
        url = reverse(iotype)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(FailedNotification.objects.count(), 1)

        failed = FailedNotification.objects.get()

        self.assertEqual(failed.status_code, 204)
        self.assertEqual(failed.timestamp, make_aware(datetime(2019, 1, 1, 12, 0, 0)))
        self.assertEqual(failed.app, "catalogi")
        self.assertEqual(failed.model, "ZaakType")
        self.assertEqual(failed.instance, failed.data)
