# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import List, Tuple

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_better_admin_arrayfield.forms.fields import DynamicArrayField
from notifications_api_common.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
)
from rest_framework import exceptions
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.scopes import SCOPE_REGISTRY

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.components.catalogi.models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakType,
)
from openzaak.utils import build_absolute_url
from openzaak.utils.auth import get_auth
from openzaak.utils.middleware import override_request_host
from openzaak.utils.validators import ResourceValidator

from .constants import RelatedTypeSelectionMethods
from .utils import (
    get_applicatie_serializer,
    send_applicatie_changed_notification,
    versions_equivalent,
)
from .validators import validate_authorizations_have_scopes


class ApplicatieForm(forms.ModelForm):
    class Meta:
        model = Applicatie
        # removed `client_ids arrayfield - replaced by and inline
        # doing stuff with JWTSecret
        fields = ("uuid", "label", "heeft_alle_autorisaties")

    def save(self, *args, **kwargs):
        if self.instance.client_ids is None:
            self.instance.client_ids = []
        return super().save(*args, **kwargs)


class CredentialsBaseFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance")
        queryset = kwargs.pop("queryset")
        kwargs.pop("save_as_new", None)

        if instance.client_ids:
            kwargs["queryset"] = queryset.filter(identifier__in=instance.client_ids)
        else:
            kwargs["queryset"] = queryset.none()

        self.instance = instance

        super().__init__(*args, **kwargs)

        # add default value for secret = ''
        self.form.base_fields["secret"].required = False
        self.form.base_fields["secret"].initial = ""

    @classmethod
    def get_default_prefix(cls):
        return "credentials"

    def save(self, *args, **kwargs):
        commit = kwargs.get("commit", True)
        creds = super().save(*args, **kwargs)

        old_identifiers = {
            form.instance.pk: form.initial["identifier"]
            for form in self.forms
            if form.instance.pk and "identifier" in form.initial
        }

        for cred in self.deleted_objects:
            self.instance.client_ids.remove(cred.identifier)

        for cred, changed in self.changed_objects:
            if "identifier" not in changed:
                continue

            old_identifier = old_identifiers[cred.id]
            self.instance.client_ids.remove(old_identifier)
            self.instance.client_ids.append(cred.identifier)

        for cred in creds:
            if cred.identifier in self.instance.client_ids:
                continue
            self.instance.client_ids.append(cred.identifier)

        if commit:
            self.instance.save(update_fields=["client_ids"])
        return creds


CredentialsFormSet = forms.modelformset_factory(
    JWTSecret,
    formset=CredentialsBaseFormSet,
    fields=("identifier", "secret"),
    extra=1,
    can_delete=True,
)


# Forms used for autorisaties in custom view - we use them for validation
# purposes, the actual rendering/dynamic behaviour is taken care off by
# React.

COMPONENT_TO_PREFIXES_MAP = {
    ComponentTypes.zrc: ("audittrails", "notificaties", "zaken"),
    ComponentTypes.drc: ("audittrails", "notificaties", "documenten"),
    ComponentTypes.ztc: ("notificaties", "catalogi"),
    ComponentTypes.brc: ("audittrails", "notificaties", "besluiten"),
    ComponentTypes.nrc: ("notificaties",),
    ComponentTypes.ac: ("notificaties", "autorisaties"),
}

COMPONENT_TO_FIELDS_MAP = {
    ComponentTypes.zrc: {
        "required": ("related_type_selection", "vertrouwelijkheidaanduiding"),
        "types_field": "zaaktypen",
        "_autorisatie_type_field": "zaaktype",
        "verbose_name": _("zaaktype"),
        "resource_name": "ZaakType",
    },
    ComponentTypes.drc: {
        "required": ("related_type_selection", "vertrouwelijkheidaanduiding"),
        "types_field": "informatieobjecttypen",
        "_autorisatie_type_field": "informatieobjecttype",
        "verbose_name": _("informatieobjecttype"),
        "resource_name": "InformatieObjectType",
    },
    ComponentTypes.brc: {
        "required": ("related_type_selection",),
        "types_field": "besluittypen",
        "_autorisatie_type_field": "besluittype",
        "verbose_name": _("besluittype"),
        "resource_name": "BesluitType",
    },
}


def get_scope_choices() -> List[Tuple[str, str]]:
    labels = {scope.label for scope in SCOPE_REGISTRY if not scope.children}.union(
        {SCOPE_NOTIFICATIES_CONSUMEREN_LABEL, SCOPE_NOTIFICATIES_PUBLICEREN_LABEL}
    )
    labels = sorted(labels)
    return list(zip(labels, labels))


class AutorisatieForm(forms.Form):
    component = forms.ChoiceField(
        label=_("component"),
        required=True,
        help_text=_("Component waarin deze autorisatie van toepassing is."),
        choices=ComponentTypes.choices,
        widget=forms.RadioSelect,
    )
    scopes = forms.MultipleChoiceField(
        label=_("scopes"),
        required=True,
        help_text=_("Scopes die van toepassing zijn binnen deze autorisatie"),
        choices=get_scope_choices,
        widget=forms.CheckboxSelectMultiple,
    )

    related_type_selection = forms.ChoiceField(
        label=_("{verbose_name}"),
        required=False,
        help_text=_(
            "Kies hoe je gerelateerde typen wil aanduiden. "
            "De toegekende scopes zijn enkel van toepassing op objecten van "
            "dit/deze specifieke {verbose_name_plural}"
        ),
        choices=RelatedTypeSelectionMethods.choices,
        widget=forms.RadioSelect,
    )

    vertrouwelijkheidaanduiding = forms.ChoiceField(
        label=_("maximale vertrouwelijkheidaanduiding"),
        required=False,
        help_text=_(
            "De maximale vertrouwelijkheidaanduiding waartoe consumers toegang hebben. "
            "Indien objecten van het betreffende {verbose_name} een striktere "
            "vertrouwelijkheidaanduiding hebben, dan zijn deze objecten niet "
            "toegangelijk voor de consumer."
        ),
        choices=VertrouwelijkheidsAanduiding.choices,
        widget=forms.RadioSelect,
    )

    catalogi = forms.ModelMultipleChoiceField(
        label=_("catalogi"),
        required=False,
        help_text=_("De catalogi waarvoor deze Autorisatie geldt."),
        queryset=Catalogus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    zaaktypen = forms.ModelMultipleChoiceField(
        label=_("zaaktypen"),
        required=False,
        help_text=_("De zaaktypen waarop deze autorisatie van toepassing is."),
        queryset=ZaakType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
    informatieobjecttypen = forms.ModelMultipleChoiceField(
        label=_("informatieobjecttypen"),
        required=False,
        help_text=_(
            "De informatieobjecttypen waarop deze autorisatie van toepassing is."
        ),
        queryset=InformatieObjectType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
    besluittypen = forms.ModelMultipleChoiceField(
        label=_("besluittypen"),
        required=False,
        help_text=_("De besluittypen waarop deze autorisatie van toepassing is."),
        queryset=BesluitType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
    externe_typen = DynamicArrayField(
        base_field=forms.URLField(
            max_length=1000,
            required=True,
        ),
        required=False,
        error_messages={"item_invalid": ""},
    )

    def has_changed(self) -> bool:
        # We don't consider an empty form that was left empty changed
        if not self.initial:
            return super().has_changed()

        # When saving the AutorisatieBaseFormSet, we delete all of the existing
        # Autorisaties/CatalogusAutorisaties and subsequently save the submitted forms
        # to save the changes that were made. In case certain AutorisatieForms were left
        # unchanged, the default behavior of `BaseForm.has_changed` would be to return `False`.
        # However, `has_changed=False` means that the `AutorisatieForm.save` will not
        # have access to `cleaned_data` and exit early, which means that the Autorisatie
        # will not be created.

        # For this reason we always want to ensure `has_changed` is True here, to ensure
        # the Autorisatie/CatalogusAutorisatie is (re)created, no matter what
        return True

    def clean(self):
        super().clean()

        component = self.cleaned_data.get("component")

        # didn't pass validation, can't do anything else as it all relies on this
        # field
        if not component:
            return

        self._validate_scopes(component)
        self._validate_required_fields(component)
        self._validate_external_types(component)

    def _validate_scopes(self, component: str):
        scopes = self.cleaned_data.get("scopes")
        # can't do anything if there are no scopes selected
        if scopes is None:
            return

        valid_prefixes = COMPONENT_TO_PREFIXES_MAP[component]
        invalid_scopes = [
            scope
            for scope in scopes
            if not any(scope.startswith(prefix) for prefix in valid_prefixes)
        ]

        if invalid_scopes:
            error = forms.ValidationError(
                _(
                    "De volgende scopes zijn geen geldige keuzes voor deze component: {scopes}"
                ).format(scopes=", ".join(invalid_scopes)),
                code="invalid",
            )
            self.add_error("scopes", error)

    def _validate_required_fields(self, component: str):
        _field_info = COMPONENT_TO_FIELDS_MAP.get(component)
        if _field_info is None:
            return

        expected_fields = _field_info["required"]
        missing = [
            field for field in expected_fields if not self.cleaned_data.get(field)
        ]

        for field in missing:
            error = forms.ValidationError(
                _("Je moet een keuze opgeven voor het veld: {field}").format(
                    field=field
                ),
                code="required",
            )
            self.add_error(field, error)

        if "related_type_selection" not in expected_fields:
            return

        related_type_selection = self.cleaned_data.get("related_type_selection")
        if related_type_selection != RelatedTypeSelectionMethods.manual_select:
            return

        # check that values for the typen have been selected manually
        types_field = _field_info["types_field"]
        if not self.cleaned_data.get(types_field) and not self.cleaned_data.get(
            "externe_typen"
        ):
            error = forms.ValidationError(
                _("Je moet minimaal 1 {verbose_name} kiezen").format(
                    verbose_name=_field_info["verbose_name"]
                ),
                code="required",
            )
            self.add_error(types_field, error)

    def _validate_external_types(self, component):
        _field_info = COMPONENT_TO_FIELDS_MAP.get(component)
        if _field_info is None:
            return

        external_typen = self.cleaned_data.get("externe_typen")

        if not external_typen:
            return

        validator = ResourceValidator(
            _field_info["resource_name"], settings.ZTC_API_STANDARD, get_auth=get_auth
        )
        for _type in external_typen:
            try:
                validator(_type)
            except exceptions.ValidationError as exc:
                error = forms.ValidationError(
                    str(exc.detail[0]), code=exc.detail[0].code
                )
                self.add_error("externe_typen", error)

    def get_types(self, component):
        related_type_selection = self.cleaned_data.get("related_type_selection")
        types = None
        if related_type_selection:
            _field_info = COMPONENT_TO_FIELDS_MAP[component]

            # only pick a queryset of the explicitly selected objects
            if related_type_selection == RelatedTypeSelectionMethods.select_catalogus:
                catalogi = self.cleaned_data["catalogi"]
                types = []
                for catalogus in catalogi:
                    types += list(
                        getattr(
                            catalogus, f"{_field_info['_autorisatie_type_field']}_set"
                        ).all()
                    )
            elif related_type_selection == RelatedTypeSelectionMethods.manual_select:
                types = self.cleaned_data.get(_field_info["types_field"])

        return types

    def save(self, applicatie: Applicatie, request, commit=True):
        """
        Save the Autorisatie data into the right Autorisatie objects.

        The form essentially condenses a bunch of fields, e.g. for each
        included 'zaaktype' an Autorisatie object is created.
        """
        if not commit:
            return

        # forms beyond initial data that haven't changed -> nothing to do
        # if the form has not changed, `full_clean` will not add data to `cleaned_data`
        if not self.cleaned_data:
            return

        # Fixed fields
        component = self.cleaned_data["component"]
        scopes = self.cleaned_data["scopes"]

        # dependent fields
        vertrouwelijkheidaanduiding = self.cleaned_data.get(
            "vertrouwelijkheidaanduiding", ""
        )

        types = self.get_types(component)
        # install a handler for future objects
        related_type_selection = self.cleaned_data.get("related_type_selection")
        if related_type_selection == RelatedTypeSelectionMethods.select_catalogus:
            instance_pks = []
            for catalogus in self.cleaned_data.get("catalogi", []):
                instance = CatalogusAutorisatie.objects.create(
                    applicatie=applicatie,
                    component=component,
                    catalogus=catalogus,
                    scopes=scopes,
                    max_vertrouwelijkheidaanduiding=vertrouwelijkheidaanduiding,
                )
                instance_pks.append(instance.pk)

            # In case a CatalogusAutorisatie in created, we don't want to create Autorisaties
            return

        autorisatie_kwargs = {
            "applicatie": applicatie,
            "component": component,
            "scopes": scopes,
        }

        if types is None:
            Autorisatie.objects.create(**autorisatie_kwargs)
        else:
            _field_info = COMPONENT_TO_FIELDS_MAP[component]
            autorisaties = []
            for _type in types:
                data = autorisatie_kwargs.copy()

                # signal uses build_absolute_url to find autorisaties to delete
                data[_field_info["_autorisatie_type_field"]] = build_absolute_url(
                    _type.get_absolute_api_url()
                )
                autorisaties.append(
                    Autorisatie(
                        max_vertrouwelijkheidaanduiding=vertrouwelijkheidaanduiding,
                        **data,
                    )
                )
            if self.cleaned_data.get("externe_typen"):
                for _type in self.cleaned_data.get("externe_typen"):
                    data = autorisatie_kwargs.copy()
                    data[_field_info["_autorisatie_type_field"]] = _type
                    autorisaties.append(
                        Autorisatie(
                            max_vertrouwelijkheidaanduiding=vertrouwelijkheidaanduiding,
                            **data,
                        )
                    )

            Autorisatie.objects.bulk_create(autorisaties)


class AutorisatieBaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.applicatie = kwargs.pop("applicatie")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    @transaction.atomic
    def save(self, commit=True):
        # use the API representation to figure out if there were any changes
        # we have to explicitly override the request host (because this is not an API request)
        # to ensure the notification has the right URLs
        override_request_host(self.request)

        old_version = get_applicatie_serializer(
            self.applicatie, request=self.request
        ).data

        self.applicatie.autorisaties.all().delete()
        # In case a component was changed for an existing CatalogusAutorisatie, we don't
        # want to have to figure out which row was changed and delete that row. Instead
        # we delete all existing CatalogusAutorisaties and save all the forms in the
        # formset, because the end result should always be the same as the submitted form
        # data
        self.applicatie.catalogusautorisatie_set.all().delete()
        for form in self.forms:
            form.save(applicatie=self.applicatie, request=self.request, commit=commit)

        new_version = get_applicatie_serializer(
            self.applicatie, request=self.request
        ).data

        if not versions_equivalent(old_version, new_version):
            send_applicatie_changed_notification(self.applicatie, new_version)

    def clean(self):
        self._validate_authorizations_have_scopes()
        # validate overlap zaaktypen between different auths
        self._validate_overlapping_types()
        self._validate_catalogus_autorisaties_overlapping_component_and_catalogus()

    def _validate_authorizations_have_scopes(self):
        data = [form.cleaned_data for form in self.forms if form.cleaned_data]
        validate_authorizations_have_scopes(data)

    def _validate_overlapping_types(self):
        scope_types = {}
        for form in self.forms:
            if form.cleaned_data:
                component = form.cleaned_data["component"]
                types = set(form.get_types(component) or [])
                scopes = form.cleaned_data["scopes"]
                types_field = None
                if component in COMPONENT_TO_FIELDS_MAP:
                    types_field = COMPONENT_TO_FIELDS_MAP[component]["types_field"]
                for scope in scopes:
                    previous_types = scope_types.get(scope, set())
                    if previous_types.intersection(types):
                        raise ValidationError(
                            _("{field} may not have overlapping scopes.").format(
                                field=types_field
                            ),
                            code="overlapped_types",
                        )
                    # for components without types just check scopes
                    if scope in scope_types and not scope_types[scope] and not types:
                        raise ValidationError(
                            _("Scopes in {component} may not be duplicated.").format(
                                component=component
                            ),
                            code="overlapped_types",
                        )

                    scope_types[scope] = previous_types.union(types)

    def _validate_catalogus_autorisaties_overlapping_component_and_catalogus(self):
        """
        Raise errors if there are any CatalogusAutorisaties with the same component and
        catalogus (or regular Autorisaties with the same component and types from the same catalogus)
        regardless of scopes

        * if there are the 2 same catalogi for CatalogusAutorisaties - error
        * if there is a catalog for CatalogusAutorisaties and a type of the same catalog for Autorisaties - error
        * If there are types of the same catalog for Autorisaties - no error
        """
        error_msg = _(
            "You cannot create multiple Autorisaties/CatalogusAutorisaties with the "
            "same component and catalogus: {component}, {catalogus}"
        )
        catalogus_and_component_combinations = []
        type_catalogus_and_component_combinations = []
        for form in self.forms:
            data = form.cleaned_data

            if not data:
                continue

            match data.get("related_type_selection"):
                case RelatedTypeSelectionMethods.select_catalogus:
                    for catalogus in data.get("catalogi", []):
                        catalogus_and_component = (catalogus.pk, data["component"])
                        if (
                            catalogus_and_component
                            in catalogus_and_component_combinations
                        ) or (
                            catalogus_and_component
                            in type_catalogus_and_component_combinations
                        ):
                            raise ValidationError(
                                error_msg.format(
                                    component=data["component"], catalogus=catalogus
                                ),
                                code="overlapped_component_and_catalogus",
                            )
                        else:
                            catalogus_and_component_combinations.append(
                                catalogus_and_component
                            )
                case RelatedTypeSelectionMethods.manual_select:
                    _field_info = COMPONENT_TO_FIELDS_MAP.get(data["component"])
                    if not _field_info:
                        continue

                    for _type in data.get(_field_info["types_field"], []):
                        catalogus_and_component = (
                            _type.catalogus.pk,
                            data["component"],
                        )
                        if (
                            catalogus_and_component
                            in catalogus_and_component_combinations
                        ):
                            raise ValidationError(
                                error_msg.format(
                                    component=data["component"],
                                    catalogus=_type.catalogus,
                                ),
                                code="overlapped_component_and_catalogus",
                            )
                        else:
                            type_catalogus_and_component_combinations.append(
                                catalogus_and_component
                            )


# TODO: support external zaaktypen
AutorisatieFormSet = forms.formset_factory(
    AutorisatieForm, extra=1, formset=AutorisatieBaseFormSet
)
