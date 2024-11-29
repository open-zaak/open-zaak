# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import ZaakBesluitForm


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
