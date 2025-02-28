# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase
from django.urls import reverse

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ResultaatTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import Resultaat
from openzaak.tests.utils import AdminTestMixin

from ..factories import ResultaatFactory, ZaakFactory


@disable_admin_mfa()
class ResultaatAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def test_valid_create_resultaat(self):
        zaak = ZaakFactory.create()
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_resultaattype": resultaattype.id,
            "toelichting": "desc",
        }
        self.client.post(reverse("admin:zaken_resultaat_add"), data)

        self.assertEqual(Resultaat.objects.count(), 1)
        resultaat = Resultaat.objects.get()
        self.assertEqual(resultaat.resultaattype, resultaattype)
        self.assertEqual(resultaat.zaak, zaak)
        self.assertEqual(resultaat.resultaattype.zaaktype, resultaat.zaak.zaaktype)

    def test_invalid_create_resultaat(self):
        # check_zaaktype validation
        catalogus = CatalogusFactory.create()
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus)
        zaak = ZaakFactory.create(zaaktype=zaaktype1)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype2)

        data = {
            "uuid": uuid.uuid4(),
            "zaak": zaak.id,
            "_resultaattype": resultaattype.id,
            "toelichting": "desc",
        }
        response = self.client.post(reverse("admin:zaken_resultaat_add"), data)

        self.assertEqual(Resultaat.objects.count(), 0)
        self.assertContains(
            response, "De referentie hoort niet bij het zaaktype van de zaak."
        )
        self.assertEqual(Resultaat.objects.count(), 0)

    def test_valid_update_resultaat(self):
        zaak = ZaakFactory.create()
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        resultaat = ResultaatFactory.create(
            toelichting="old",
            resultaattype=resultaattype,
            zaak=zaak,
        )

        self.client.post(
            reverse("admin:zaken_resultaat_change", args=(resultaat.pk,)),
            {"toelichting": "new"},
        )

        resultaat = Resultaat.objects.get()
        self.assertEqual(resultaat.resultaattype, resultaattype)
        self.assertEqual(resultaat.zaak, zaak)
        self.assertEqual(resultaat.resultaattype.zaaktype, resultaat.zaak.zaaktype)
