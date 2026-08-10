# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.zaken.admin import ZaakEigenschapForm


@disable_admin_mfa()
class TestZaakEigenschapForm(TestCase):
    def test_zaakeigenschap_form_clean_does_not_throw_exception_if_eigenschap_is_given(
        self,
    ):
        form = ZaakEigenschapForm()
        form.cleaned_data = {
            "eigenschap": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")
