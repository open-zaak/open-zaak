# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa

from openzaak.components.documenten.admin import (
    GebruiksrechtenForm,
)

from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


@disable_admin_mfa()
class TestGebruiksrechtenForm(TestCase):
    def test_bestandsdeel_form_throws_exception_if_informatieobject_does_not_have_version(
        self,
    ):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        form = GebruiksrechtenForm()
        form.cleaned_data = {
            "informatieobject": canonical,
        }
        with self.assertRaises(forms.ValidationError):
            form.clean()
