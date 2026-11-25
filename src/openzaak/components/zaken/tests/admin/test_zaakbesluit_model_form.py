# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.audittrails.models import AuditTrail

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.zaken.admin import ZaakBesluitForm
from openzaak.components.zaken.models import ZaakBesluit
from openzaak.components.zaken.tests.factories import ZaakFactory


@disable_admin_mfa()
class TestZaakBesluitForm(TestCase):
    def test_zaakbesluit_form_clean_does_not_throw_exception_if_besluit_is_given(self):
        form = ZaakBesluitForm()
        form.cleaned_data = {
            "besluit": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakbesluit_form_invalid_if_besluit_is_not_given(
        self,
    ):
        form = ZaakBesluitForm()
        form.cleaned_data = {}
        self.assertFalse(form.is_valid())


@disable_admin_mfa()
class TestZaakBesluitAdminDelete(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

    def test_delete_selected_zaakbesluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(
            besluittype__catalogus=zaak.zaaktype.catalogus, zaak=zaak
        )
        zaakbesluit = ZaakBesluit.objects.get(zaak=zaak, besluit=besluit)
        url = reverse("admin:zaken_zaakbesluit_changelist")

        response = self.app.get(url, user=self.user)
        form = response.forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [str(zaakbesluit.pk)]
        confirm = form.submit()
        confirm.forms[1].submit()

        self.assertFalse(ZaakBesluit.objects.filter(pk=zaakbesluit.pk).exists())
        trail = AuditTrail.objects.get()
        self.assertEqual(trail.resource, "zaakbesluit")
        self.assertEqual(trail.hoofd_object, trail.resource_url)
        self.assertIn(str(zaak.uuid), trail.hoofd_object)
        besluit.refresh_from_db()
        self.assertIsNone(besluit.zaak)

    def test_delete_zaakbesluit_removes_zaak_from_besluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(
            besluittype__catalogus=zaak.zaaktype.catalogus, zaak=zaak
        )
        zaakbesluit = ZaakBesluit.objects.get(zaak=zaak, besluit=besluit)
        url = reverse("admin:zaken_zaakbesluit_delete", args=(zaakbesluit.pk,))

        response = self.app.get(url, user=self.user)
        response.forms[1].submit()

        self.assertFalse(ZaakBesluit.objects.filter(pk=zaakbesluit.pk).exists())
        besluit.refresh_from_db()
        self.assertIsNone(besluit.zaak)

    def test_delete_zaakbesluit_does_not_touch_besluit_of_other_zaak(self):
        zaak = ZaakFactory.create()
        other_zaak = ZaakFactory.create(zaaktype=zaak.zaaktype)
        besluit = BesluitFactory.create(
            besluittype__catalogus=zaak.zaaktype.catalogus, zaak=other_zaak
        )
        zaakbesluit = ZaakBesluit.objects.create(zaak=zaak, besluit=besluit)
        url = reverse("admin:zaken_zaakbesluit_delete", args=(zaakbesluit.pk,))

        response = self.app.get(url, user=self.user)
        response.forms[1].submit()

        self.assertFalse(ZaakBesluit.objects.filter(pk=zaakbesluit.pk).exists())
        besluit.refresh_from_db()
        self.assertEqual(besluit.zaak, other_zaak)
        self.assertTrue(
            ZaakBesluit.objects.filter(zaak=other_zaak, besluit=besluit).exists()
        )
