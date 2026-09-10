# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.zaken.admin import ZaakBesluitForm


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
