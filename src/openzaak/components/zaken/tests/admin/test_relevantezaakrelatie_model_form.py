# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from openzaak.components.zaken.admin import RelevanteZaakRelatieForm


class TestRelevanteZaakRelatieForm(TestCase):
    def test_relevantezaakrelatie_form_clean_does_not_throw_exception_if_relevant_zaak_is_given(
        self,
    ):
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {
            "_relevant_zaak": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_relevantezaakrelatie_form_clean_does_not_throw_exception_if_relevant_zaak_url_is_given(
        self,
    ):
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {
            "_relevant_zaak_url": "https://testserver",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_relevantezaakrelatie_form_clean_throws_exception_if_relevant_zaak_and_relevant_zaak_url_are_not_given(
        self,
    ):
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
