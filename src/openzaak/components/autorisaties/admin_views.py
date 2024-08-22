# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Union

from django import forms
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from django_loose_fk.loaders import BaseLoader
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes

from openzaak.components.catalogi.models import Catalogus
from openzaak.utils.admin import AdminContextMixin

from .admin_serializers import CatalogusSerializer
from .constants import RelatedTypeSelectionMethods
from .forms import (
    COMPONENT_TO_FIELDS_MAP,
    COMPONENT_TO_PREFIXES_MAP,
    AutorisatieFormSet,
    VertrouwelijkheidsAanduiding,
    get_scope_choices,
)
from .models import CatalogusAutorisatie
from .utils import get_related_object


def get_form_data(form: forms.Form) -> Dict[str, Dict]:
    """
    Serialize the form data and errors for the frontend.
    """
    errors = (
        {
            field: [{"msg": next(iter(error)), "code": error.code} for error in _errors]
            for field, _errors in form.errors.as_data().items()
        }
        if form.is_bound
        else {}
    )

    values = {field.name: field.value() for field in form}
    return {
        "errors": errors,
        "values": values,
    }


def is_local_url(autorisatie):
    loader = BaseLoader()
    if autorisatie.component == ComponentTypes.zrc:
        return loader.is_local_url(autorisatie.zaaktype)
    elif autorisatie.component == ComponentTypes.drc:
        return loader.is_local_url(autorisatie.informatieobjecttype)
    elif autorisatie.component == ComponentTypes.brc:
        return loader.is_local_url(autorisatie.besluittype)
    return True


def get_initial_for_component(
    component: str,
    autorisaties: List[Autorisatie],
) -> List[Dict[str, Any]]:
    _related_objs = {}
    _related_objs_external = {}

    internal_autorisaties = []
    external_autorisaties = []

    for autorisatie in autorisaties:
        if is_local_url(autorisatie):
            obj = get_related_object(autorisatie)
            _related_objs[autorisatie.pk] = obj
            internal_autorisaties.append(autorisatie)
        else:
            type_field = COMPONENT_TO_FIELDS_MAP[component]["_autorisatie_type_field"]
            _related_objs_external[autorisatie.pk] = getattr(autorisatie, type_field)
            external_autorisaties.append(autorisatie)

    related_objs = {pk: obj.id for pk, obj in _related_objs.items() if obj is not None}

    initial = []

    if component == ComponentTypes.zrc:
        grouped_by_va = defaultdict(list)
        for autorisatie in internal_autorisaties + external_autorisaties:
            grouped_by_va[autorisatie.max_vertrouwelijkheidaanduiding].append(
                autorisatie
            )

        for va, _autorisaties in grouped_by_va.items():
            _initial = {"vertrouwelijkheidaanduiding": va}
            relevant_ids = {
                related_objs[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in related_objs
            }
            relevant_external = [
                _related_objs_external[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in _related_objs_external
            ]

            if _autorisaties:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                        "zaaktypen": relevant_ids,
                        "externe_typen": relevant_external,
                    }
                )
            initial.append(_initial)

    elif component == ComponentTypes.drc:
        grouped_by_va = defaultdict(list)
        for autorisatie in internal_autorisaties + external_autorisaties:
            grouped_by_va[autorisatie.max_vertrouwelijkheidaanduiding].append(
                autorisatie
            )

        for va, _autorisaties in grouped_by_va.items():
            _initial = {"vertrouwelijkheidaanduiding": va}
            relevant_ids = {
                related_objs[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in related_objs
            }
            relevant_external = [
                _related_objs_external[autorisatie.pk]
                for autorisatie in _autorisaties
                if autorisatie.pk in _related_objs_external
            ]

            if _autorisaties:
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.manual_select,
                        "informatieobjecttypen": relevant_ids,
                        "externe_typen": relevant_external,
                    }
                )
            initial.append(_initial)

    elif component == ComponentTypes.brc:
        relevant_ids = set(related_objs.values())
        _initial = {
            "externe_typen": list(_related_objs_external.values()),
            "related_type_selection": RelatedTypeSelectionMethods.manual_select,
            "besluittypen": relevant_ids,
        }
        initial.append(_initial)
    else:
        # The other components do not have any extra options
        initial.append({})

    return initial


def get_initial_for_component_for_catalogus_autorisaties(
    component: str,
    catalogus_autorisaties: list[CatalogusAutorisatie],
) -> List[Dict[str, Any]]:
    initial = []

    match component:
        case ComponentTypes.zrc | ComponentTypes.drc:
            grouped_by_va = defaultdict(list)
            for autorisatie in catalogus_autorisaties:
                grouped_by_va[autorisatie.max_vertrouwelijkheidaanduiding].append(
                    autorisatie
                )

            for va, _autorisaties in grouped_by_va.items():
                _initial = {"vertrouwelijkheidaanduiding": va}
                catalogus_autorisaties_for_va = [
                    catalogus_autorisatie.catalogus.pk
                    for catalogus_autorisatie in _autorisaties or []
                ]
                _initial.update(
                    {
                        "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                        "catalogi": catalogus_autorisaties_for_va,
                    }
                )
                initial.append(_initial)
        case ComponentTypes.brc:
            initial = [
                {
                    "related_type_selection": RelatedTypeSelectionMethods.select_catalogus,
                    "catalogi": [
                        catalogus_autorisatie.catalogus.pk
                        for catalogus_autorisatie in catalogus_autorisaties or []
                    ],
                }
            ]

    return initial


def _get_group_key(
    spec: Union[Autorisatie, CatalogusAutorisatie]
) -> Tuple[str, Tuple[str]]:
    return (spec.component, tuple(sorted(spec.scopes)))


def get_initial(applicatie: Applicatie) -> List[Dict[str, Any]]:
    """
    Figure out the initial data for the formset, showing existing config.

    We group applicatie autorisaties bij (component, scopes) and evaluate
    if this constitutes one of the "special" options. If so, we can provide
    this information to the form, presenting it much more condensed to the
    end user.
    """
    initial = []

    grouped_catalogus_autorisaties = defaultdict(list)
    for catalogus_autorisatie in applicatie.catalogusautorisatie_set.all():
        key = _get_group_key(catalogus_autorisatie)
        grouped_catalogus_autorisaties[key].append(catalogus_autorisatie)

    grouped_autorisaties = defaultdict(list)
    for autorisatie in applicatie.autorisaties.all():
        key = _get_group_key(autorisatie)
        grouped_autorisaties[key].append(autorisatie)

    for (
        component,
        _scopes,
    ), catalogus_autorisaties in grouped_catalogus_autorisaties.items():
        component_initial = get_initial_for_component_for_catalogus_autorisaties(
            component,
            catalogus_autorisaties,
        )
        initial += [
            {"component": component, "scopes": list(_scopes), **_initial}
            for _initial in component_initial
        ]

    for (component, _scopes), _autorisaties in grouped_autorisaties.items():
        component_initial = get_initial_for_component(
            component,
            _autorisaties,
        )
        initial += [
            {"component": component, "scopes": list(_scopes), **_initial}
            for _initial in component_initial
        ]

    return initial


class AutorisatiesView(AdminContextMixin, DetailView):
    model = Applicatie
    template_name = "admin/autorisaties/applicatie_autorisaties.html"
    pk_url_kwarg = "object_id"
    # set these on the .as_view(...) call
    admin_site = None
    model_admin = None

    # perform permission checks
    def dispatch(self, request, *args, **kwargs):
        assert self.admin_site
        assert self.model_admin

        applicatie = self.get_object()
        if not self.model_admin.has_change_permission(request, applicatie):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = applicatie = self.get_object()
        formset = self.get_formset()

        if formset.is_valid():
            formset.save()
            return redirect(
                "admin:authorizations_applicatie_change", object_id=applicatie.pk
            )

        context = self.get_context_data(formset=formset)
        return self.render_to_response(context)

    def get_formset(self):
        initial = get_initial(self.object)
        data = self.request.POST if self.request.method == "POST" else None
        return AutorisatieFormSet(
            data=data, initial=initial, applicatie=self.object, request=self.request
        )

    def get_context_data(self, **kwargs):
        formset = kwargs.pop("formset", self.get_formset())
        kwargs["formset"] = formset

        context = super().get_context_data(**kwargs)

        catalogi = Catalogus.objects.prefetch_related(
            "zaaktype_set",
            "informatieobjecttype_set",
            "besluittype_set",
        )

        context.update(
            {
                "opts": Applicatie._meta,
                "original": self.get_object(),
                "title": _("beheer autorisaties"),
                "is_popup": False,
                "formset_config": {
                    "prefix": formset.prefix,
                    "extra": formset.extra,
                    **{
                        field.name: int(field.value())
                        for field in formset.management_form
                    },
                },
                "scope_choices": get_scope_choices(),
                "COMPONENTS_TO_PREFIXES_MAP": COMPONENT_TO_PREFIXES_MAP,
                "RELATED_TYPE_SELECTION_METHODS": RelatedTypeSelectionMethods.choices,
                "VA_CHOICES": VertrouwelijkheidsAanduiding.choices,
                "catalogi": CatalogusSerializer(
                    catalogi, read_only=True, many=True
                ).data,
                "formdata": [get_form_data(form) for form in formset],
            }
        )

        return context
