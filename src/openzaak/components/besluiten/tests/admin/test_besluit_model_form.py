# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from openzaak.components.besluiten.admin import BesluitForm


class TestBesluitForm(TestCase):
    def test_besluit_form_clean_does_not_throw_exception_if_besluittype_is_given(self):
        form = BesluitForm()
        form.cleaned_data = {
            "_besluittype": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_besluit_form_clean_does_not_throw_exception_if_besluittype_url_is_given(
        self,
    ):
        form = BesluitForm()
        form.cleaned_data = {
            "_besluittype_url": "https://testserver",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_besluit_form_clean_throws_exception_if_besluittype_and_besluittype_url_are_not_given(
        self,
    ):
        form = BesluitForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
