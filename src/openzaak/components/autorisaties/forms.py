from typing import List, Tuple

from django import forms
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.notifications.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
)
from vng_api_common.scopes import SCOPE_REGISTRY

from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
    ZaakType,
)


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
    },
    ComponentTypes.drc: {
        "required": ("related_type_selection", "vertrouwelijkheidaanduiding"),
        "types_field": "informatieobjecttypen",
    },
    ComponentTypes.brc: {
        "required": ("related_type_selection",),
        "types_field": "besluittypen",
    },
}


class RelatedTypeSelectionMethods(DjangoChoices):
    all_current = ChoiceItem("all_current", _("Alle huidige {verbose_name_plural}"))
    all_current_and_future = ChoiceItem(
        "all_current_and_future", _("Alle huidige en toekomstige {verbose_name_plural}")
    )
    manual_select = ChoiceItem("manual_select", _("Selecteer handmatig"))


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

    zaaktypen = forms.ModelMultipleChoiceField(
        label=_("zaaktypen"),
        required=False,
        help_text=_("De zaaktypen waarop deze autorisatie van toepassing is."),
        queryset=ZaakType.objects.filter(concept=False),
        widget=forms.CheckboxSelectMultiple,
    )
    informatieobjecttypen = forms.ModelMultipleChoiceField(
        label=_("zaaktypen"),
        required=False,
        help_text=_("De zaaktypen waarop deze autorisatie van toepassing is."),
        queryset=InformatieObjectType.objects.filter(concept=False),
        widget=forms.CheckboxSelectMultiple,
    )
    besluittypen = forms.ModelMultipleChoiceField(
        label=_("zaaktypen"),
        required=False,
        help_text=_("De zaaktypen waarop deze autorisatie van toepassing is."),
        queryset=BesluitType.objects.filter(concept=False),
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        super().clean()

        component = self.cleaned_data.get("component")

        # didn't pass validation, can't do anything else as it all relies on this
        # field
        if not component:
            return

        self._validate_scopes(component)
        self._validate_required_fields(component)

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
            raise forms.ValidationError(
                _(
                    "De volgende scopes zijn geen geldige keuzes voor deze component: {scopes}"
                ).format(scopes=", ".join(invalid_scopes)),
                code="invalid",
            )

    def _validate_required_fields(self, component: str):
        expected_fields = COMPONENT_TO_FIELDS_MAP[component]["required"]
        missing = [
            field for field in expected_fields if not self.cleaned_data.get(field)
        ]

        if missing:
            raise forms.ValidationError(
                _("Je moet een keuze opgeven voor de/het veld(en): {fields}").format(
                    fields=", ".join(missing)
                ),
                code="required",
                params={"fields": missing},
            )

        if "related_type_selection" not in expected_fields:
            return

        related_type_selection = self.cleaned_data["related_type_selection"]
        if related_type_selection != RelatedTypeSelectionMethods.manual_select:
            return

        # check that values for the typen have been selected manually
        types_field = COMPONENT_TO_FIELDS_MAP[component]["types_field"]
        if not self.cleaned_data.get(types_field):
            raise forms.ValidationError(
                {
                    types_field: forms.ValidationError(
                        _("Je moet minimaal 1 type kiezen"), code="required",
                    )
                }
            )


# TODO: validate overlap zaaktypen between different auths
# TODO: support external zaaktypen
# TODO: validate dependent fields
AutorisatieFormSet = forms.formset_factory(AutorisatieForm, extra=3)
