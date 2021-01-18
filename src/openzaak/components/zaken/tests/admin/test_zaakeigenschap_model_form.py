# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from openzaak.components.zaken.admin import ZaakEigenschapForm


class TestZaakEigenschapForm(TestCase):
    def test_zaakeigenschap_form_clean_does_not_throw_exception_if_eigenschap_is_given(
        self,
    ):
        form = ZaakEigenschapForm()
        form.cleaned_data = {
            "_eigenschap": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakeigenschap_form_clean_does_not_throw_exception_if_eigenschap_url_is_given(
        self,
    ):
        form = ZaakEigenschapForm()
        form.cleaned_data = {
            "_eigenschap_url": "https://testserver",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakeigenschap_form_clean_throws_exception_if_eigenschap_and_eigenschap_url_are_not_given(
        self,
    ):
        form = ZaakEigenschapForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
