# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.audittrails.models import AuditTrail
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

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
            "_besluit": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakbesluit_form_clean_does_not_throw_exception_if_besluit_url_is_given(
        self,
    ):
        brc_service = ServiceFactory.create(
            api_type=APITypes.brc,
            api_root="https://external.besluiten.nl/api/v1/",
        )
        form = ZaakBesluitForm()
        form.cleaned_data = {
            "_besluit_base_url": brc_service.id,
            "_besluit_relative_url": "besluiten/1",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakbesluit_form_clean_throws_exception_if_besluit_and_besluit_url_are_not_given(
        self,
    ):
        form = ZaakBesluitForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()


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
        zaakbesluit = ZaakBesluit.objects.get(zaak=zaak, _besluit=besluit)
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
