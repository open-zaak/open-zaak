from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

import requests
from django_better_admin_arrayfield.forms.fields import DynamicArrayField
from rest_framework.exceptions import ValidationError
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)
from vng_api_common.validators import ResourceValidator

from openzaak.forms.widgets import BooleanRadio
from openzaak.selectielijst.admin import get_selectielijst_resultaat_choices

from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..models import ResultaatType, ZaakType


class ZaakTypeForm(forms.ModelForm):
    class Meta:
        model = ZaakType
        fields = "__all__"
        widgets = {
            "opschorting_en_aanhouding_mogelijk": BooleanRadio,
            "verlenging_mogelijk": BooleanRadio,
            "publicatie_indicatie": BooleanRadio,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["opschorting_en_aanhouding_mogelijk"].widget.required = True
        self.fields["verlenging_mogelijk"].widget.required = True
        self.fields["publicatie_indicatie"].widget.required = True

    def clean(self):
        super().clean()

        for name, field in self.fields.items():
            if not isinstance(field, DynamicArrayField):
                continue

            model_field = self._meta.model._meta.get_field(name)
            if model_field.null:
                continue

            if name not in self.cleaned_data:
                continue  # didn't pass field level validation

            if self.cleaned_data[name] is not None:
                continue  # non-empty value, no need to correct anything

            default_value = model_field.default
            if callable(default_value):
                default_value = default_value()
            self.cleaned_data[name] = default_value

        if "_addversion" in self.data:
            self._clean_datum_einde_geldigheid()

    def _clean_datum_einde_geldigheid(self):
        datum_einde_geldigheid = self.cleaned_data.get("datum_einde_geldigheid")

        if not datum_einde_geldigheid:
            msg = _(
                "datum_einde_geldigheid is required if the new version is being created"
            )
            self.add_error(
                "datum_einde_geldigheid", forms.ValidationError(msg, code="invalid"),
            )


class ResultaatTypeForm(forms.ModelForm):
    class Meta:
        model = ResultaatType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            proces_type = self.instance.zaaktype.selectielijst_procestype
            self.fields[
                "selectielijstklasse"
            ].choices = get_selectielijst_resultaat_choices(proces_type)

    def clean(self):
        super().clean()

        self._clean_selectielijstklasse()
        self._clean_brondatum_archiefprocedure_afleidingswijze()
        self._clean_brondatum_archiefprocedure()

    def _get_field_label(self, field: str) -> str:
        return self.fields[field].label

    def _clean_selectielijstklasse(self):
        """
        Validate that the selectielijstklasse is relevant for the zaaktype.procestype
        """
        selectielijstklasse = self.cleaned_data.get("selectielijstklasse")
        zaaktype = self.cleaned_data.get("zaaktype")

        if not selectielijstklasse or not zaaktype:
            # nothing to do
            return

        response = requests.get(selectielijstklasse)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            msg = (
                _("URL %s for selectielijstklasse did not resolve")
                % selectielijstklasse
            )
            err = forms.ValidationError(msg, code="invalid")
            raise forms.ValidationError({"selectielijstklasse": err}) from exc

        validator = ResourceValidator("Resultaat", settings.VRL_API_SPEC)
        try:
            # Check whether the url points to a Resultaat
            validator(selectielijstklasse)
        except ValidationError as exc:
            err = forms.ValidationError(exc.detail[0], code=exc.detail[0].code)
            raise forms.ValidationError({"selectielijstklasse": err}) from exc

        procestype = response.json()["procesType"]
        if procestype != zaaktype.selectielijst_procestype:
            if not zaaktype.selectielijst_procestype:
                edit_zaaktype = reverse(
                    "admin:catalogi_zaaktype_change", args=(zaaktype.pk,)
                )
                err = format_html(
                    '{msg} <a href="{url}#id_selectielijst_procestype">{url_text}</a>',
                    msg=_(
                        "Er is geen Selectielijst-procestype gedefinieerd op het zaaktype!"
                    ),
                    url=edit_zaaktype,
                    url_text=_("Zaaktype bewerken"),
                )

                self.add_error("selectielijstklasse", err)
            else:
                msg = _(
                    "De selectielijstklasse hoort niet bij het selectielijst "
                    "procestype van het zaaktype"
                )
                self.add_error(
                    "selectielijstklasse", forms.ValidationError(msg, code="invalid")
                )

    def _clean_brondatum_archiefprocedure_afleidingswijze(self):
        """
        Validate that the afleidingswijze matches the selectielijstklasse.

        There's two cases that are determined, the rest cannot be checked
        automatically:

        * if the selectielijst.resultaat.procestermijn is nihil, afleidingswijze
          must be 'afgehandeld'
        * if the selectielijst.resultaat.procestermijn is a fixed period,
          afleidingswijze must be 'termijn'
        """
        MAPPING = {
            Procestermijn.nihil: Afleidingswijze.afgehandeld,
            Procestermijn.ingeschatte_bestaansduur_procesobject: Afleidingswijze.termijn,
        }
        REVERSE_MAPPING = {value: key for key, value in MAPPING.items()}

        selectielijstklasse = self.cleaned_data.get("selectielijstklasse")
        afleidingswijze = self.cleaned_data.get(
            "brondatum_archiefprocedure_afleidingswijze"
        )

        # nothing to validate, exit early...
        if not selectielijstklasse or not afleidingswijze:
            return

        response = requests.get(selectielijstklasse)
        procestermijn = response.json()["procestermijn"]

        # mapping selectielijst -> ZTC
        forward_not_ok = (
            procestermijn in MAPPING and afleidingswijze != MAPPING[procestermijn]
        )
        if forward_not_ok:
            value_label = Afleidingswijze.labels[MAPPING[procestermijn]]
            msg = (
                _(
                    "Invalide afleidingswijze gekozen, volgens de selectielijst moet dit %s zijn"
                )
                % value_label
            )
            self.add_error(
                "brondatum_archiefprocedure_afleidingswijze",
                forms.ValidationError(msg, code="invalid"),
            )

        # mapping ZTC -> selectielijst!
        backward_not_ok = (
            afleidingswijze in REVERSE_MAPPING
            and REVERSE_MAPPING[afleidingswijze] != procestermijn
        )
        if backward_not_ok:
            msg = _("Invalide afleidingswijze gekozen volgens de selectielijst")
            self.add_error(
                "brondatum_archiefprocedure_afleidingswijze",
                forms.ValidationError(msg, code="invalid"),
            )

    def _clean_brondatum_archiefprocedure(self):
        """
        Clean the parametrization of how to determine brondatum archief.

        Per https://www.gemmaonline.nl/index.php/Imztc_2.2/doc/enumeration/afleidingswijzebrondatumarchiefprocedure
        it's clear that some `afleidingswijze` choices restrict possible values
        of other attributes in the same groepattribuut.

        More rules are described in https://www.gemmaonline.nl/index.php/Imztc_2.2/doc
        /attribuutsoort/resultaattype.brondatum_archiefprocedure.einddatum_bekend
        """

        # these values of afleidingswijze forbid you to set values for
        # the other parameter fields
        ONLY_AFLEIDINGSWIJZE = (
            Afleidingswijze.afgehandeld,
            Afleidingswijze.gerelateerde_zaak,
            Afleidingswijze.hoofdzaak,
            Afleidingswijze.ingangsdatum_besluit,
            Afleidingswijze.vervaldatum_besluit,
        )

        # these values of afleidingswijze make the value of einddatum_bekend
        # irrelevant - it's only relevant if it's a datumkenmerk of the process-object
        EINDDATUM_BEKEND_IRRELEVANT = (
            Afleidingswijze.afgehandeld,
            Afleidingswijze.termijn,
        )

        # these are the extra parameter fields that are sometimes required,
        # sometimes not
        PARAMETER_FIELDS = (
            "brondatum_archiefprocedure_datumkenmerk",
            "brondatum_archiefprocedure_objecttype",
            "brondatum_archiefprocedure_registratie",
            "brondatum_archiefprocedure_procestermijn",
        )

        MSG_FIELD_FORBIDDEN = "Het veld '{verbose_name}' mag niet ingevuld zijn als de afleidingswijze '{value}' is"
        MSG_FIELD_REQUIRED = (
            "Het veld '{verbose_name}' is verplicht als de afleidingswijze '{value}' is"
        )

        # read out the values
        afleidingswijze = self.cleaned_data.get(
            "brondatum_archiefprocedure_afleidingswijze"
        )
        if not afleidingswijze:
            return

        afleidingswijze_label = Afleidingswijze.labels[afleidingswijze]
        einddatum_bekend = self.cleaned_data.get(
            "brondatum_archiefprocedure_einddatum_bekend"
        )
        datumkenmerk = self.cleaned_data.get("brondatum_archiefprocedure_datumkenmerk")

        if afleidingswijze in ONLY_AFLEIDINGSWIJZE:
            for field in PARAMETER_FIELDS:
                value = self.cleaned_data.get(field)
                if value:
                    msg = MSG_FIELD_FORBIDDEN.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="invalid"))

        # do not allow einddatum_bekend to be set to True if the value is not relevant
        if (
            afleidingswijze in EINDDATUM_BEKEND_IRRELEVANT and einddatum_bekend is True
        ):  # noqa
            msg = MSG_FIELD_FORBIDDEN.format(
                verbose_name=self._get_field_label(
                    "brondatum_archiefprocedure_einddatum_bekend"
                ),
                value=afleidingswijze_label,
            )
            self.add_error(
                "brondatum_archiefprocedure_einddatum_bekend",
                forms.ValidationError(msg, code="invalid"),
            )

        if afleidingswijze == Afleidingswijze.termijn:

            for field in (
                "brondatum_archiefprocedure_datumkenmerk",
                "brondatum_archiefprocedure_objecttype",
                "brondatum_archiefprocedure_registratie",
            ):
                value = self.cleaned_data.get(field)
                if value:
                    msg = MSG_FIELD_FORBIDDEN.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="invalid"))

            termijn = self.cleaned_data.get("brondatum_archiefprocedure_procestermijn")
            if not termijn:
                msg = MSG_FIELD_REQUIRED.format(
                    verbose_name=self._get_field_label(
                        "brondatum_archiefprocedure_procestermijn"
                    ),
                    value=afleidingswijze_label,
                )
                self.add_error(
                    "brondatum_archiefprocedure_procestermijn",
                    forms.ValidationError(msg, code="required"),
                )

        # eigenschap - only ZAAKen have eigenschappen, so objecttype/registratie are not relevant
        if afleidingswijze == Afleidingswijze.eigenschap:
            for field in (
                "brondatum_archiefprocedure_objecttype",
                "brondatum_archiefprocedure_registratie",
                "brondatum_archiefprocedure_procestermijn",
            ):
                value = self.cleaned_data.get(field)
                if value:
                    msg = MSG_FIELD_FORBIDDEN.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="invalid"))

            if not datumkenmerk:
                msg = MSG_FIELD_REQUIRED.format(
                    verbose_name=self._get_field_label(
                        "brondatum_archiefprocedure_datumkenmerk"
                    ),
                    value=afleidingswijze_label,
                )
                self.add_error(
                    "brondatum_archiefprocedure_datumkenmerk",
                    forms.ValidationError(msg, code="required"),
                )

        # zaakobject - the object is already related to the ZAAK, so we don't need
        # the 'registratie' to be able to figure out where it lives
        # the other two fields are required so that ZRC can filter on objectType to
        # get the correct object(s) and datumkenmerk to know which attribute to inspect
        if afleidingswijze == Afleidingswijze.zaakobject:
            for field in (
                "brondatum_archiefprocedure_registratie",
                "brondatum_archiefprocedure_procestermijn",
            ):
                value = self.cleaned_data.get(field)
                if value:
                    msg = MSG_FIELD_FORBIDDEN.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="invalid"))

            for field in (
                "brondatum_archiefprocedure_objecttype",
                "brondatum_archiefprocedure_datumkenmerk",
            ):
                value = self.cleaned_data.get(field)
                if not value:
                    msg = MSG_FIELD_REQUIRED.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="required"))

        # ander datumkenmerk -> we need everything
        if afleidingswijze == Afleidingswijze.ander_datumkenmerk:
            for field in PARAMETER_FIELDS:
                value = self.cleaned_data.get(field)
                if not value:
                    msg = MSG_FIELD_REQUIRED.format(
                        verbose_name=self._get_field_label(field),
                        value=afleidingswijze_label,
                    )
                    self.add_error(field, forms.ValidationError(msg, code="required"))


class CatalogusImportForm(forms.Form):
    file = forms.FileField(
        label=_("bestand"),
        required=True,
        help_text=_("Het ZIP-bestand met de catalogus."),
    )
    generate_new_uuids = forms.BooleanField(
        label=_("Genereer nieuwe UUIDs"),
        initial=True,
        help_text=_(
            "Zorgt ervoor dat er nieuwe UUIDs gegenereerd worden "
            "in plaats van dat de bestaande UUIDs uit het bestand gebruikt worden"
        ),
        required=False,
    )
