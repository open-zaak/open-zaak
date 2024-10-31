# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.admin import BesluitInformatieObjectForm


@disable_admin_mfa()
class TestBesluitInformatieObjectForm(TestCase):
    def test_besluit_information_object_form_clean_does_not_throw_exception_if_informatieobject_is_given(
        self,
    ):
        form = BesluitInformatieObjectForm()
        form.cleaned_data = {
            "_informatieobject": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_besluit_information_object_form_clean_does_not_throw_exception_if_informatieobject_url_is_given(
        self,
    ):
        service = ServiceFactory.create(
            api_root="http://example.org/catalogi/", api_type=APITypes.drc
        )
        form = BesluitInformatieObjectForm()
        form.cleaned_data = {"_informatieobject_base_url": service.id}
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_besluit_information_object_form_throws_exception_if_informatieobject_and_url_are_not_given(
        self,
    ):
        form = BesluitInformatieObjectForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
