import datetime
from unittest import skip

from django.utils import timezone

from openzaak.components.zaken.api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN, SCOPEN_ZAKEN_HEROPENEN
)
from openzaak.components.zaken.api.tests.utils import get_operation_url
from openzaak.components.zaken.models.constants import BetalingsIndicatie
from openzaak.components.zaken.models.tests.factories import ZaakFactory
from openzaak.components.catalogi.models.tests.factories import StatusTypeFactory
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import Archiefnominatie
from vng_api_common.tests import JWTAuthMixin, reverse


class ZaakClosedTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_update_zaak_open(self):
        zaak = ZaakFactory.create(betalingsindicatie=BetalingsIndicatie.geheel)
        url = reverse(zaak)

        response = self.client.patch(url, {
            'betalingsindicatie': BetalingsIndicatie.nvt,
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.json()['betalingsindicatie'], BetalingsIndicatie.nvt)
        zaak.refresh_from_db()
        self.assertEqual(zaak.betalingsindicatie, BetalingsIndicatie.nvt)

    @skip('Current implementation is without authentication')
    def test_update_zaak_closed_not_allowed(self):
        zaak = ZaakFactory.create(einddatum=timezone.now())
        url = reverse(zaak)

        response = self.client.patch(url, {
            'betalingsindicatie': BetalingsIndicatie.nvt,
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip('Current implementation is without authentication')
    def test_update_zaak_closed_allowed(self):
        zaak = ZaakFactory.create(einddatum=timezone.now())
        url = reverse(zaak)

        self.autorisatie.scopes = [SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        self.autorisatie.save()

        response = self.client.patch(url, {
            'betalingsindicatie': BetalingsIndicatie.nvt,
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    @skip('Current implementation is without authentication')
    def test_reopenzaak_allowed(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(),
            archiefactiedatum='2020-01-01',
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
        )
        statustype = StatusTypeFactory.create()
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url('status_create')

        self.autorisatie.scopes = [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        data = {
            'zaak': reverse(zaak),
            'statustype': statustype_url,
            'datumStatusGezet': datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)
        self.assertIsNone(zaak.archiefactiedatum)
        self.assertIsNone(zaak.archiefnominatie)

    @skip('Current implementation is without authentication')
    def test_reopenzaak_not_allowed(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(),
        )
        statustype = StatusTypeFactory.create()
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url('status_create')
        self.autorisatie.scopes = [SCOPE_STATUSSEN_TOEVOEGEN]
        self.autorisatie.save()

        data = {
            'zaak': reverse(zaak),
            'statustype': statustype_url,
            'datumStatusGezet': datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data['detail'], 'Reopening a closed case with current scope is forbidden')
