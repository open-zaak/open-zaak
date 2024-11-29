# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import StatusForm


@disable_admin_mfa()
class TestStatusForm(TestCase):
    def test_status_form_clean_does_not_throw_exception_if_statustype_is_given(self):
        form = StatusForm()
        form.cleaned_data = {
            "_statustype": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_status_form_clean_does_not_throw_exception_if_statustype_url_is_given(
        self,
    ):
        ztc_service = ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root="https://external.catalogi.nl/api/v1/",
        )
        form = StatusForm()
        form.cleaned_data = {
            "_statustype_base_url": ztc_service.id,
            "_statustype_relative_url": "statustypen/1",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_status_form_clean_throws_exception_if_statustype_and_statustype_url_are_not_given(
        self,
    ):
        form = StatusForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
