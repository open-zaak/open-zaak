# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from vng_api_common.constants import ObjectTypes

from openzaak.components.documenten.admin import ObjectInformatieObjectForm


class TestObjectInformatieObjectForm(TestCase):
    def test_objectinformationobject_form_clean_does_not_throw_exception_if_zaak_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {"object_type": ObjectTypes.zaak, "_zaak": 1}
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_objectinformationobject_form_clean_does_not_throw_exception_if_zaak_url_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {
            "object_type": ObjectTypes.zaak,
            "_zaak_url": "https://testserver",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_objectinformationobject_form_clean_throws_exception_if_neither_zaak_or_zaak_url_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {"object_type": ObjectTypes.zaak}
        with self.assertRaises(forms.ValidationError):
            form.clean()

    def test_objectinformationobject_form_clean_does_not_throw_exception_if_besluit_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {"object_type": ObjectTypes.besluit, "_besluit": 1}
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_objectinformationobject_form_clean_does_not_throw_exception_if_besluit_url_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {
            "object_type": ObjectTypes.besluit,
            "_besluit_url": "https://testserver",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_objectinformationobject_form_clean_throws_exception_if_neither_besluit_or_besluit_url_is_given(
        self,
    ):
        form = ObjectInformatieObjectForm()
        form.cleaned_data = {"object_type": ObjectTypes.besluit}
        with self.assertRaises(forms.ValidationError):
            form.clean()
