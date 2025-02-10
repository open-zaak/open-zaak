# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    EigenschapFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import ZaakEigenschap
from openzaak.tests.utils import AdminTestMixin

from ..factories import ZaakEigenschapFactory, ZaakFactory


@disable_admin_mfa()
class ZaakEigenschapAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_valid_create_zaakeigenschap(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(zaaktype=zaak.zaaktype)
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_eigenschap": eigenschap.id,
            "_naam": "some name",
            "waarde": "test",
        }
        self.client.post(reverse("admin:zaken_zaakeigenschap_add"), data)

        self.assertEqual(ZaakEigenschap.objects.count(), 1)
        zaakeigenschap = ZaakEigenschap.objects.get()
        self.assertEqual(zaakeigenschap.eigenschap, eigenschap)
        self.assertEqual(zaakeigenschap.zaak, zaak)
        self.assertEqual(
            zaakeigenschap.eigenschap.zaaktype, zaakeigenschap.eigenschap.zaaktype
        )

    def test_invalid_create_zaakeigenschap(self):
        catalogus = CatalogusFactory.create()
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus)
        zaak = ZaakFactory.create(zaaktype=zaaktype1)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype2)
        self.assertEqual(ZaakEigenschap.objects.count(), 0)

        add_url = reverse("admin:zaken_zaakeigenschap_add")
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_eigenschap": eigenschap.id,
            "_naam": "some name",
            "waarde": "test",
        }

        self.client.post(add_url, data)
        response = self.client.post(add_url, data)

        self.assertEqual(ZaakEigenschap.objects.count(), 0)
        self.assertContains(
            response, "De referentie hoort niet bij het zaaktype van de zaak."
        )

    def test_valid_update_zaakeigenschap(self):
        zaakeigenschap = ZaakEigenschapFactory.create(_naam="old")
        change_url = reverse(
            "admin:zaken_zaakeigenschap_change", args=(zaakeigenschap.pk,)
        )
        data = {
            "uuid": zaakeigenschap.uuid,
            "zaak": zaakeigenschap.zaak.id,
            "_eigenschap": zaakeigenschap.eigenschap.id,
            "_naam": "new",
            "waarde": "test",
        }
        self.client.post(change_url, data)

        zaakeigenschap = ZaakEigenschap.objects.get()
        self.assertEqual(ZaakEigenschap.objects.count(), 1)
        self.assertEqual(
            zaakeigenschap.eigenschap.zaaktype, zaakeigenschap.eigenschap.zaaktype
        )
