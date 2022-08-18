# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.zaken.admin import ZaakInformatieObjectForm


class TestZaakInformatieObjectForm(TestCase):
    def test_zaakinformatieobject_form_clean_does_not_throw_exception_if_informatieobject_is_given(
        self,
    ):
        form = ZaakInformatieObjectForm()
        form.cleaned_data = {
            "_informatieobject": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakinformatieobject_form_clean_does_not_throw_exception_if_informatieobject_url_is_given(
        self,
    ):
        drc_service = Service.objects.create(
            api_type=APITypes.ztc, api_root="https://external.documenten.nl/api/v1/",
        )
        form = ZaakInformatieObjectForm()
        form.cleaned_data = {
            "_informatieobject_base_url": drc_service.id,
            "_informatieobject_relative_url": "io/1",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakinformatieobject_form_clean_throws_exception_if_informatieobject_and_url_are_not_given(
        self,
    ):
        form = ZaakInformatieObjectForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
