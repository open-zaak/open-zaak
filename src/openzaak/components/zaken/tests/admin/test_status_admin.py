# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import Status
from openzaak.tests.utils import AdminTestMixin

from ..factories import StatusFactory, ZaakFactory


@disable_admin_mfa()
class StatusAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_valid_create_status(self):
        zaak = ZaakFactory.create()
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)

        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_statustype": statustype.id,
            "datum_status_gezet_0": date(2018, 1, 1),
            "datum_status_gezet_1": time(10, 0, 0),
        }

        self.client.post(reverse("admin:zaken_status_add"), data)

        status = Status.objects.get()
        self.assertEqual(Status.objects.count(), 1)
        self.assertEqual(status.statustype, statustype)
        self.assertEqual(status.zaak, zaak)
        self.assertEqual(status.statustype.zaaktype, status.zaak.zaaktype)

    def test_invalid_create_status(self):
        # check_zaaktype validation
        catalogus = CatalogusFactory.create()
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus)
        zaak = ZaakFactory.create(zaaktype=zaaktype1)
        statustype = StatusTypeFactory.create(zaaktype=zaaktype2)

        self.assertEqual(Status.objects.count(), 0)

        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_statustype": statustype.id,
            "datum_status_gezet_0": date(2018, 1, 1),
            "datum_status_gezet_1": time(10, 0, 0),
        }
        response = self.client.post(reverse("admin:zaken_status_add"), data)

        self.assertEqual(Status.objects.count(), 0)
        self.assertContains(
            response, "De referentie hoort niet bij het zaaktype van de zaak."
        )

    def test_valid_update_status(self):
        status = StatusFactory.create(statustoelichting="old")
        statustype = StatusTypeFactory.create(zaaktype=status.zaak.zaaktype)
        data = {
            "uuid": status.uuid,
            "zaak": status.zaak.id,
            "_statustype": statustype.id,
            "datum_status_gezet_0": timezone.now().date(),
            "datum_status_gezet_1": timezone.now().time(),
            "statustoelichting": "new",
        }

        self.client.post(reverse("admin:zaken_status_change", args=(status.pk,)), data)

        status = Status.objects.get()
        self.assertEqual(Status.objects.count(), 1)
        self.assertEqual(status.statustype, statustype)
        self.assertEqual(status.statustype.zaaktype, status.zaak.zaaktype)
