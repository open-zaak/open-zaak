# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import RolForm


@disable_admin_mfa()
class TestRolForm(TestCase):
    def test_rol_form_clean_does_not_throw_exception_if_roltype_is_given(self):
        form = RolForm()
        form.cleaned_data = {
            "_roltype": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_rol_form_clean_does_not_throw_exception_if_roltype_url_is_given(self):
        ztc_service = ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root="https://external.catalogi.nl/api/v1/",
        )
        form = RolForm()
        form.cleaned_data = {
            "_roltype_base_url": ztc_service.id,
            "_roltype_relative_url": "roltypen/1",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_rol_form_clean_throws_exception_if_roltype_and_roltype_url_are_not_given(
        self,
    ):
        form = RolForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
