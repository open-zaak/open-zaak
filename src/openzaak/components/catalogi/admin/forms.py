# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib.admin.sites import site
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ValidationError as _ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

import requests
from django_loose_fk.loaders import BaseLoader
from rest_framework.exceptions import ValidationError
from vng_api_common.client import ClientError, get_client, to_internal_data
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)
from vng_api_common.tests import reverse as _reverse

from openzaak.forms.widgets import BooleanRadio
from openzaak.selectielijst.admin_fields import get_selectielijst_resultaat_choices
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.utils import build_absolute_url
from openzaak.utils.validators import ResourceValidator

from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..models import (
    BesluitType,
    InformatieObjectType,
    ResultaatType,
    ZaakType,
    ZaakTypeInformatieObjectType,
    ZaakTypenRelatie,
)
from ..validators import validate_brondatumarchiefprocedure
from .widgets import CatalogusFilterFKRawIdWidget, CatalogusFilterM2MRawIdWidget

EMPTY_SELECTIELIJSTKLASSE_CHOICES = (
    (
        "",
        _(
            "Please select a Procestype for the related ZaakType to "
            "get proper filtering of selectielijstklasses"
        ),
    ),
)


class ZaakTypeForm(forms.ModelForm):
    selectielijst_reset = forms.BooleanField(
        label=_("Reset selectielijst configuration"),
        required=False,
        initial=False,
        help_text=_(
            "Reset the selectielijstprocestype for the zaaktype and all "
            "selectielijstklassen specified for the attached resultaattypen. You need "
            "to check this if you want to change the selectielijstprocestype of a "
            "zaaktype."
        ),
    )

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

        self._make_required("opschorting_en_aanhouding_mogelijk")
        self._make_required("verlenging_mogelijk")
        self._make_required("publicatie_indicatie")

        # properly set the default for selectielijst_jaar from the global config,
        # as the django admin has no hook for specifying initial and otherwise the
        # instance `None` value is used.
        if (
            "selectielijst_procestype_jaar" in self.initial
            and self.initial["selectielijst_procestype_jaar"] is None
        ):
            referentielijst_config = ReferentieLijstConfig.get_solo()
            self.initial["selectielijst_procestype_jaar"] = (
                referentielijst_config.default_year
            )

    def _make_required(self, field: str):
        if field not in self.fields:
            return
        self.fields[field].widget.required = True

    def has_changed(self):
        # Since Django thinks the below fields are always changed we
        #   need to manually check them ourselves

        for field in [
            "initial-producten_of_diensten",
            "initial-verantwoordingsrelatie",
            "initial-trefwoorden",
            "selectielijst_procestype_jaar",
        ]:
            if field in self.data and self.data[field] != str(
                getattr(self.instance, field.replace("initial-", ""))
            ):
                return True

        changed_data = [
            data
            for data in self.changed_data
            if data
            not in (
                "trefwoorden",
                "producten_of_diensten",
                "verantwoordingsrelatie",
                "selectielijst_procestype_jaar",
            )
        ]

        return bool(changed_data)

    def clean_selectielijst_procestype(self):
        # #970 -- check that if the procestype from selectielijst changes, this does
        # not break the consistency with the selectielijstklasse specified in each
        # resultaattype
        procestype_url = self.cleaned_data["selectielijst_procestype"]
        # create instead of update -> no validation required
        if not self.instance.pk:
            return procestype_url

        # if we are resetting, there's no reason to run validation
        if self.cleaned_data.get("selectielijst_reset"):
            return procestype_url

        selectielijstklassen = (
            self.instance.resultaattypen.exclude(selectielijstklasse="")
            .values_list("selectielijstklasse", flat=True)
            .distinct()
        )
        #  no existing selectielijstklassen specified -> nothing to validate
        if not selectielijstklassen:
            return procestype_url

        # fetch the selectielijstklasse and compare that relations are still consistent
        for url in selectielijstklassen:
            client = get_client(url, raise_exceptions=False)
            if client is None:
                self.add_error(
                    None, _("Could not build a client for {url}").format(url=url)
                )
                continue

            resultaat = to_internal_data(client.get(url))

            if resultaat["procesType"] != procestype_url:
                raise forms.ValidationError(
                    _(
                        "You cannot change the procestype because there are resultaatypen "
                        "attached to this zaaktype with a selectielijstklasse belonging "
                        "to the current procestype."
                    ),
                    code="invalid",
                )

        return procestype_url


class ResultaatTypeForm(forms.ModelForm):
    # set by filthy admin voodoo in ResultaatTypeAdmin.get_form as a class attribute
    _zaaktype = None

    class Meta:
        model = ResultaatType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # for tests
        if _zaaktype := kwargs.pop("_zaaktype", None):
            self._zaaktype = _zaaktype
        super().__init__(*args, **kwargs)

        if not self.instance.pk and self._zaaktype:
            self.instance.zaaktype = self._zaaktype

        if self.instance.zaaktype_id:
            proces_type = self.instance.zaaktype.selectielijst_procestype
            if "selectielijstklasse" in self.fields:
                self.fields["selectielijstklasse"].choices = (
                    get_selectielijst_resultaat_choices(proces_type)
                )

        # make the selectielijstklasse field readonly if we don't have sufficient
        # information to validate/filter it
        if not self._zaaktype or not self._zaaktype.selectielijst_procestype:
            self.fields["selectielijstklasse"].required = False
            self.fields["selectielijstklasse"].disabled = True
            self.fields["selectielijstklasse"].choices = (
                EMPTY_SELECTIELIJSTKLASSE_CHOICES
            )

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

        client = get_client(selectielijstklasse, raise_exceptions=False)
        if client is None:
            self.add_error(
                "selectielijstklasse",
                forms.ValidationError(
                    _(
                        "Could not determine the selectielijstklasse service for URL {url}"
                    ).format(url=selectielijstklasse),
                    code="invalid",
                ),
            )
            return

        try:
            selectielijst_resultaat = to_internal_data(client.get(selectielijstklasse))
        except (ClientError, requests.RequestException) as exc:
            msg = (
                _("URL %s for selectielijstklasse did not resolve")
                % selectielijstklasse
            )
            err = forms.ValidationError(msg, code="invalid")
            raise forms.ValidationError({"selectielijstklasse": err}) from exc

        validator = ResourceValidator("Resultaat", settings.SELECTIELIJST_API_STANDARD)
        try:
            # Check whether the url points to a Resultaat
            validator(selectielijstklasse)
        except ValidationError as exc:
            err = forms.ValidationError(exc.detail[0], code=exc.detail[0].code)
            raise forms.ValidationError({"selectielijstklasse": err}) from exc

        procestype = selectielijst_resultaat["procesType"]
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

        # TODO should this use a proper client?
        response = requests.get(selectielijstklasse)
        procestermijn = response.json()["procestermijn"]

        # mapping selectielijst -> ZTC
        forward_not_ok = (
            procestermijn in MAPPING and afleidingswijze != MAPPING[procestermijn]
        )
        if forward_not_ok:
            afleidingswijze_labels = dict(
                zip(Afleidingswijze.names, Afleidingswijze.labels)
            )
            value_label = afleidingswijze_labels[MAPPING[procestermijn]]
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
            procestermijn
            and afleidingswijze in REVERSE_MAPPING
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
        afleidingswijze = self.cleaned_data.get(
            "brondatum_archiefprocedure_afleidingswijze"
        )
        if not afleidingswijze:  # earlier validation errors
            return

        data = {
            "afleidingswijze": self.cleaned_data[
                "brondatum_archiefprocedure_afleidingswijze"
            ],
            "datumkenmerk": self.cleaned_data[
                "brondatum_archiefprocedure_datumkenmerk"
            ],
            "einddatum_bekend": self.cleaned_data[
                "brondatum_archiefprocedure_einddatum_bekend"
            ],
            "objecttype": self.cleaned_data["brondatum_archiefprocedure_objecttype"],
            "registratie": self.cleaned_data["brondatum_archiefprocedure_registratie"],
            "procestermijn": self.cleaned_data[
                "brondatum_archiefprocedure_procestermijn"
            ],
        }
        error, empty, required = validate_brondatumarchiefprocedure(data)

        if not error:
            return

        afleidingswijze_labels = dict(
            zip(Afleidingswijze.names, Afleidingswijze.labels)
        )
        afleidingswijze_label = afleidingswijze_labels[afleidingswijze]
        MSG_FIELD_FORBIDDEN = "Het veld '{verbose_name}' mag niet ingevuld zijn als de afleidingswijze '{value}' is"
        MSG_FIELD_REQUIRED = (
            "Het veld '{verbose_name}' is verplicht als de afleidingswijze '{value}' is"
        )

        # add the validation errors
        for key in empty:
            field = f"brondatum_archiefprocedure_{key}"
            msg = MSG_FIELD_FORBIDDEN.format(
                verbose_name=self._get_field_label(field),
                value=afleidingswijze_label,
            )
            self.add_error(field, forms.ValidationError(msg, code="invalid"))

        for key in required:
            field = f"brondatum_archiefprocedure_{key}"
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


class ZaakTypeImportForm(forms.Form):

    identificatie_prefix = forms.CharField(
        label=_("identificatie prefix"),
        required=False,
        help_text=_("Zaaktype identification prefix. Leave blank to use imported."),
    )

    file = forms.FileField(
        label=_("bestand"),
        required=True,
        help_text=_("Het ZIP-bestand met het zaaktype."),
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


class ExistingTypeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        catalogus_pk = kwargs.pop("catalogus_pk", None)
        label = kwargs.pop("label", None)
        kwargs.pop("labels", None)
        super().__init__(*args, **kwargs)

        if catalogus_pk:
            self.fields["existing"].queryset = self.fields["existing"].queryset.filter(
                catalogus=catalogus_pk
            )
            self.fields["existing"].label = label


class ExistingInformatieObjectTypeForm(ExistingTypeForm):
    existing = forms.ModelChoiceField(
        queryset=InformatieObjectType.objects.all().order_by(
            "omschrijving", "datum_begin_geldigheid"
        ),
        required=False,
        empty_label=_("Create new"),
    )


class ExistingBesluitTypeForm(ExistingTypeForm):
    existing = forms.ModelChoiceField(
        queryset=BesluitType.objects.all().order_by(
            "omschrijving", "datum_begin_geldigheid"
        ),
        required=False,
        empty_label=_("Create new"),
    )


class BaseFormSet(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        if "labels" in kwargs:
            kwargs["label"] = kwargs["labels"][index]
        return kwargs


InformatieObjectTypeFormSet = forms.formset_factory(
    ExistingInformatieObjectTypeForm, extra=0, formset=BaseFormSet
)
BesluitTypeFormSet = forms.formset_factory(
    ExistingBesluitTypeForm, extra=0, formset=BaseFormSet
)


class BesluitTypeAdminForm(forms.ModelForm):
    class Meta:
        model = BesluitType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        catalogus_pk = None
        if kwargs.get("instance"):
            catalogus_pk = kwargs["instance"].catalogus.pk
        elif "catalogus" in kwargs.get("initial", {}):
            catalogus_pk = kwargs["initial"].get("catalogus")

        if not catalogus_pk:
            return

        if "zaaktypen" in self.fields:
            self.fields["zaaktypen"].widget = CatalogusFilterM2MRawIdWidget(
                rel=BesluitType.zaaktypen.rel,
                admin_site=site,
                catalogus_pk=catalogus_pk,
            )
        if "informatieobjecttypen" in self.fields:
            self.fields["informatieobjecttypen"].widget = CatalogusFilterM2MRawIdWidget(
                rel=BesluitType.informatieobjecttypen.rel,
                admin_site=site,
                catalogus_pk=catalogus_pk,
            )


class ZaakTypeInformatieObjectTypeAdminForm(forms.ModelForm):
    class Meta:
        model = ZaakTypeInformatieObjectType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        catalogus_pk = (
            kwargs["instance"].informatieobjecttype.catalogus.pk
            if kwargs.get("instance")
            else kwargs.get("initial", {}).get("catalogus")
        )

        if "zaaktype" in self.fields:
            self.fields["zaaktype"].widget = CatalogusFilterFKRawIdWidget(
                rel=ZaakTypeInformatieObjectType._meta.get_field(
                    "zaaktype"
                ).remote_field,
                admin_site=site,
                catalogus_pk=catalogus_pk,
            )


class RelatedZaakTypeMultiWidget(forms.widgets.MultiWidget):
    template_name = "widgets/multiwidget.html"

    def decompress(self, value):
        if value:
            try:
                loader = BaseLoader()
                if loader.is_local_url(value):
                    uuid = value.split("/")[-1]
                    return [ZaakType.objects.get(uuid=uuid).pk, None]
            except (ZaakType.DoesNotExist, _ValidationError):
                return ["", value]
            else:
                return ["", value]
        return [None, None]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        gerelateerd_zaaktype_context = self.widgets[0].get_context(
            "id_gerelateerd_zaaktype", None, {}
        )
        gerelateerd_zaaktype_context.pop("widget")
        context.update(gerelateerd_zaaktype_context)

        zaaktype_pk = None
        if value:
            try:
                url = value[1] if isinstance(value, list) else value
                loader = BaseLoader()
                if loader.is_local_url(url):
                    uuid = url.split("/")[-1]
                    zaaktype_pk = ZaakType.objects.get(uuid=uuid).pk
            except (ZaakType.DoesNotExist, _ValidationError):
                zaaktype_pk = None

        context["link_label"], context["link_url"] = self.widgets[
            0
        ].label_and_url_for_value(zaaktype_pk)
        return context


class RelatedZaakTypeMultiValueField(forms.MultiValueField):
    def compress(self, data_list):
        """
        If an internal ZaakType was selected, determine its API url and use it
        as `gerelateerd_zaaktype`. If a URL to an external ZaakType was supplied,
        use that as `gerelateerd_zaaktype`.
        """
        if data_list[0] and data_list[1]:
            raise _ValidationError(_("Kies óf een intern, óf een extern zaaktype"))

        if data_list[0]:
            return _reverse(ZaakType.objects.get(pk=data_list[0]))
        elif data_list[1]:
            return data_list[1]


class ZaakTypenRelatieAdminForm(forms.ModelForm):
    gerelateerd_zaaktype = RelatedZaakTypeMultiValueField(
        fields=[
            forms.IntegerField(required=False),
            forms.URLField(required=False),
        ],
        widget=RelatedZaakTypeMultiWidget(
            widgets=[
                ForeignKeyRawIdWidget(
                    rel=ZaakTypenRelatie._meta.get_field("zaaktype").remote_field,
                    admin_site=site,
                ),
                forms.widgets.URLInput(attrs={"style": "width:300px;"}),
            ]
        ),
        require_all_fields=False,
        help_text=_(
            "Het gerelateerde zaaktype: er kan een intern zaaktype uit de lokale "
            "Catalogus gekozen worden met het vergrootglas; of er kan een URL "
            "van een extern zaaktype in het tweede tekstvak geplaatst worden."
        ),
    )

    class Meta:
        fields = "__all__"
        model = ZaakTypenRelatie

    def _get_validation_exclusions(self):
        exclude = super()._get_validation_exclusions()
        exclude.add("gerelateerd_zaaktype")
        return exclude

    def normalize_data(self, request, obj):
        bits = urlsplit(obj.gerelateerd_zaaktype)
        if bits.scheme and bits.netloc:
            return
        obj.gerelateerd_zaaktype = build_absolute_url(
            obj.gerelateerd_zaaktype, request=request
        )
