# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import ZaakEigenschapForm


@disable_admin_mfa()
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
        ztc_service = ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root="https://external.catalogi.nl/api/v1/",
        )
        form = ZaakEigenschapForm()
        form.cleaned_data = {
            "_eigenschap_base_url": ztc_service.id,
            "_eigenschap_relative_url": "eigenschappen/1",
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
