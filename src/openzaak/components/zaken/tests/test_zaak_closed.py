import datetime

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import Archiefnominatie, ComponentTypes
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    SCOPEN_ZAKEN_HEROPENEN,
)
from ..constants import BetalingsIndicatie
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


class ZaakClosedTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_update_zaak_open(self):
        zaak = ZaakFactory.create(
            betalingsindicatie=BetalingsIndicatie.geheel, zaaktype=self.zaaktype
        )
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.json()["betalingsindicatie"], BetalingsIndicatie.nvt)
        zaak.refresh_from_db()
        self.assertEqual(zaak.betalingsindicatie, BetalingsIndicatie.nvt)

    def test_update_zaak_closed_not_allowed(self):
        zaak = ZaakFactory.create(einddatum=timezone.now(), zaaktype=self.zaaktype)
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_zaak_closed_allowed(self):
        zaak = ZaakFactory.create(einddatum=timezone.now(), zaaktype=self.zaaktype)
        url = reverse(zaak)

        self.autorisatie.scopes = [SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        self.autorisatie.save()

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_reopenzaak_allowed(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(),
            archiefactiedatum="2020-01-01",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            zaaktype=self.zaaktype,
        )
        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)
        StatusTypeFactory.create(zaaktype=self.zaaktype)
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url("status_create")

        self.autorisatie.scopes = [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        data = {
            "zaak": reverse(zaak),
            "statustype": statustype_url,
            "datumStatusGezet": datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)
        self.assertIsNone(zaak.archiefactiedatum)
        self.assertIsNone(zaak.archiefnominatie)

    def test_reopenzaak_not_allowed(self):
        zaak = ZaakFactory.create(einddatum=timezone.now(), zaaktype=self.zaaktype)
        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)
        StatusTypeFactory.create(zaaktype=self.zaaktype)
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url("status_create")
        self.autorisatie.scopes = [SCOPE_STATUSSEN_TOEVOEGEN]
        self.autorisatie.save()

        data = {
            "zaak": reverse(zaak),
            "statustype": statustype_url,
            "datumStatusGezet": datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"], "Reopening a closed case with current scope is forbidden"
        )
