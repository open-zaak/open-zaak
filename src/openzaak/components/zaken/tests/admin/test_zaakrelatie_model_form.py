# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django import forms
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.admin import ZaakRelatieForm


@disable_admin_mfa()
class ZaakRelatieFormTests(TestCase):
    def test_zaakrelatie_form_clean_does_not_throw_exception_if_gerelateerde_zaak_is_given(
        self,
    ):
        form = ZaakRelatieForm()
        form.cleaned_data = {
            "_gerelateerde_zaak": 1,
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakrelatie_form_clean_does_not_throw_exception_if_gerelateerde_zaak_url_is_given(
        self,
    ):
        zrc_service = ServiceFactory.create(
            api_type=APITypes.zrc,
            api_root="https://external.zaken.nl/api/v1/",
        )
        form = ZaakRelatieForm()
        form.cleaned_data = {
            "_gerelateerde_zaak_base_url": zrc_service.id,
            "_gerelateerde_zaak_relative_url": "zaken/1",
        }
        try:
            form.clean()
        except forms.ValidationError:
            self.fail("Exception was raised in clean function when it should not have")

    def test_zaakrelatie_form_clean_throws_exception_if_gerelateerde_zaak_and_gerelateerde_zaak_url_are_not_given(
        self,
    ):
        form = ZaakRelatieForm()
        form.cleaned_data = {}
        with self.assertRaises(forms.ValidationError):
            form.clean()
