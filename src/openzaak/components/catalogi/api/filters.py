# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from vng_api_common.filters import URLModelChoiceFilter
from vng_api_common.utils import get_help_text, get_resource_for_path

from openzaak.utils.filters import CharArrayFilter
from openzaak.utils.filterset import FilterSet
from openzaak.utils.help_text import mark_experimental

from ..models import (
    BesluitType,
    Catalogus,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakObjectType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)

# custom filter to show concept and non-concepts
STATUS_HELP_TEXT = """filter objects depending on their concept status:
* `alles`: Toon objecten waarvan het attribuut `concept` true of false is.
* `concept`: Toon objecten waarvan het attribuut `concept` true is.
* `definitief`: Toon objecten waarvan het attribuut `concept` false is (standaard).
"""
DATUM_GELDIGHEID_HELP_TEXT = "filter objecten op hun geldigheids datum."


class StatusChoices(models.TextChoices):
    alles = "alles", _("Alles")
    definitief = "definitief", _("Definitief")
    concept = "concept", _("Concept")


def status_filter(queryset, name, value: str):
    if value == StatusChoices.concept:
        return queryset.filter(**{name: True})
    elif value == StatusChoices.definitief:
        return queryset.filter(**{name: False})
    elif value == StatusChoices.alles:
        return queryset


def m2m_filter(queryset, name, value):
    parsed = urlparse(value)
    path = parsed.path
    try:
        object = get_resource_for_path(path)
    except ObjectDoesNotExist:
        return queryset.none()
    return queryset.filter(**{name: object})


def geldigheid_filter(queryset, name, value):
    """return objects which have geldigheid dates between certain date"""
    return queryset.filter(datum_begin_geldigheid__lte=value).filter(
        models.Q(datum_einde_geldigheid__gte=value)
        | models.Q(datum_einde_geldigheid__isnull=True)
    )


class RolTypeFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="zaaktype__concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype_identificatie = filters.CharFilter(
        field_name="zaaktype__identificatie",
        help_text=get_help_text("catalogi.ZaakType", "identificatie"),
    )

    class Meta:
        model = RolType
        fields = (
            "zaaktype",
            "omschrijving_generiek",
            "status",
            "datum_geldigheid",
            "zaaktype_identificatie",
        )


class ZaakTypeInformatieObjectTypeFilter(FilterSet):
    status = filters.CharFilter(
        field_name="zaaktype__concept",
        method="status_filter_m2m",
        help_text=STATUS_HELP_TEXT,
    )

    class Meta:
        model = ZaakTypeInformatieObjectType
        fields = ("zaaktype", "informatieobjecttype", "richting", "status")

    def status_filter_m2m(self, queryset, name, value):
        if value == "concept":
            return queryset.filter(
                models.Q(zaaktype__concept=True)
                | models.Q(informatieobjecttype__concept=True)
            )
        elif value == "definitief":
            return queryset.filter(
                zaaktype__concept=False, informatieobjecttype__concept=False
            )
        elif value == "alles":
            return queryset


class ResultaatTypeFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="zaaktype__concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype_identificatie = filters.CharFilter(
        field_name="zaaktype__identificatie",
        help_text=get_help_text("catalogi.ZaakType", "identificatie"),
    )

    class Meta:
        model = ResultaatType
        fields = ("zaaktype", "status", "datum_geldigheid", "zaaktype_identificatie")


class StatusTypeFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="zaaktype__concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype_identificatie = filters.CharFilter(
        field_name="zaaktype__identificatie",
        help_text=get_help_text("catalogi.ZaakType", "identificatie"),
    )

    class Meta:
        model = StatusType
        fields = ("zaaktype", "status", "datum_geldigheid", "zaaktype_identificatie")


class EigenschapFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="zaaktype__concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype_identificatie = filters.CharFilter(
        field_name="zaaktype__identificatie",
        help_text=get_help_text("catalogi.ZaakType", "identificatie"),
    )

    class Meta:
        model = Eigenschap
        fields = ("zaaktype", "status", "datum_geldigheid", "zaaktype_identificatie")


class ZaakTypeFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    trefwoorden = CharArrayFilter(field_name="trefwoorden", lookup_expr="contains")
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )

    class Meta:
        model = ZaakType
        fields = (
            "catalogus",
            "identificatie",
            "trefwoorden",
            "status",
            "datum_geldigheid",
        )


class InformatieObjectTypeFilter(FilterSet):
    status = filters.ChoiceFilter(
        field_name="concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype = extend_schema_field(OpenApiTypes.URI)(
        URLModelChoiceFilter(
            field_name="zaaktypeinformatieobjecttype__zaaktype",
            queryset=ZaakType.objects.all(),
            help_text=mark_experimental(
                get_help_text("catalogi.ZaakTypeInformatieObjectType", "zaaktype")
            ),
        )
    )

    class Meta:
        model = InformatieObjectType
        fields = ("catalogus", "status", "omschrijving", "datum_geldigheid", "zaaktype")


class BesluitTypeFilter(FilterSet):
    zaaktypen = filters.CharFilter(
        field_name="zaaktypen",
        method=m2m_filter,
        help_text=_(
            "ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit BESLUITTYPE"
        ),
        validators=[URLValidator()],
    )
    informatieobjecttypen = filters.CharFilter(
        field_name="informatieobjecttypen",
        method=m2m_filter,
        help_text=_(
            "Het INFORMATIEOBJECTTYPE van informatieobjecten waarin besluiten van dit "
            "BESLUITTYPE worden vastgelegd."
        ),
        validators=[URLValidator()],
    )
    status = filters.ChoiceFilter(
        field_name="concept",
        method=status_filter,
        help_text=STATUS_HELP_TEXT,
        choices=StatusChoices.choices,
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )

    class Meta:
        model = BesluitType
        fields = (
            "catalogus",
            "zaaktypen",
            "informatieobjecttypen",
            "status",
            "omschrijving",
            "datum_geldigheid",
        )


class CatalogusFilter(FilterSet):
    class Meta:
        model = Catalogus
        fields = {"domein": ["exact", "in"], "rsin": ["exact", "in"]}


class ZaakObjectTypeFilter(FilterSet):
    catalogus = URLModelChoiceFilter(
        field_name="zaaktype__catalogus",
        queryset=Catalogus.objects.all(),
        help_text=get_help_text("catalogi.ZaakType", "catalogus"),
    )
    datum_geldigheid = filters.DateFilter(
        method=geldigheid_filter,
        help_text=DATUM_GELDIGHEID_HELP_TEXT,
    )
    zaaktype_identificatie = filters.CharFilter(
        field_name="zaaktype__identificatie",
        help_text=get_help_text("catalogi.ZaakType", "identificatie"),
    )

    class Meta:
        model = ZaakObjectType
        fields = (
            "ander_objecttype",
            "catalogus",
            "objecttype",
            "relatie_omschrijving",
            "datum_begin_geldigheid",
            "datum_einde_geldigheid",
            "datum_geldigheid",
            "zaaktype",
            "zaaktype_identificatie",
        )
