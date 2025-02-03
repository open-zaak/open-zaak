# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import RelevanteZaakRelatieForm


@disable_admin_mfa()
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
        zrc_service = ServiceFactory.create(
            api_type=APITypes.zrc,
            api_root="https://external.zaken.nl/api/v1/",
        )
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {
            "_relevant_zaak_base_url": zrc_service.id,
            "_relevant_zaak_relative_url": "zaken/1",
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

    def test_relevantezaakrelatie_form_clean_throws_exception_if_aard_overige_and_overige_relatie_is_not_given(
        self,
    ):
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {"_relevant_zaak": 1, "aard_relatie": "overig"}
        with self.assertRaises(forms.ValidationError):
            form.clean()

    def test_relevantezaakrelatie_form_clean_does_not_throw_exception_if_aard_overige_and_overige_relatie_are_given(
        self,
    ):
        form = RelevanteZaakRelatieForm()
        form.cleaned_data = {
            "_relevant_zaak": 1,
            "aard_relatie": "overig",
            "overige_relatie": "overig",
        }

        form.clean()
