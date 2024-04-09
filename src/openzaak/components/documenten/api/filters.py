# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from django_filters import OrderingFilter, rest_framework as filters
from django_loose_fk.filters import FkOrUrlFieldFilter
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.filters import URLModelChoiceFilter
from vng_api_common.utils import get_help_text

from openzaak.components.documenten.constants import ObjectInformatieObjectTypes
from openzaak.utils.filters import CharArrayFilter, ExpandFilter
from openzaak.utils.filterset import FilterSet, NestedFkOrUrlFieldFilter
from openzaak.utils.help_text import mark_experimental

from ..models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
    Verzending,
)
from .serializers import (
    EnkelvoudigInformatieObjectSerializer,
    GebruiksrechtenSerializer,
    VerzendingSerializer,
)
from .utils import check_path

logger = logging.getLogger(__name__)


class EnkelvoudigInformatieObjectListFilter(FilterSet):
    creatiedatum__gte = filters.DateFilter(
        help_text=mark_experimental(
            "The creation date of this information object (greater or equal to the given date)."
        ),
        field_name="creatiedatum",
        lookup_expr="gte",
    )
    creatiedatum__lte = filters.DateFilter(
        help_text=mark_experimental(
            "The creation date of this information object (lesser or equal to the given date)."
        ),
        field_name="creatiedatum",
        lookup_expr="lte",
    )
    auteur = filters.CharFilter(
        help_text=mark_experimental(
            "The person or organisation that created this object."
        ),
        lookup_expr="icontains",
    )
    beschrijving = filters.CharFilter(
        help_text=mark_experimental("The description of the Information Object."),
        lookup_expr="icontains",
    )
    locked = filters.BooleanFilter(
        help_text=mark_experimental(
            "Indication of the Information Object being locked or not."
        ),
        method="locked_filter",
    )
    titel = filters.CharFilter(
        help_text=mark_experimental("Titel of the Information Object."),
        lookup_expr="icontains",
    )
    trefwoorden = CharArrayFilter(
        help_text=mark_experimental(
            "Filter on a set of keywords that contain in the Information Objects."
        ),
        lookup_expr="overlap",
    )
    vertrouwelijkheidaanduiding = filters.ChoiceFilter(
        help_text=mark_experimental(
            "The confidentiality indication of this Information object."
        ),
        choices=VertrouwelijkheidsAanduiding.choices,
    )

    zaak = NestedFkOrUrlFieldFilter(
        help_text=mark_experimental(
            "URL-referentie to the related ZAAK (in this or another API)."
        ),
        queryset=EnkelvoudigInformatieObject.objects.filter(
            Q(
                canonical__objectinformatieobject__object_type=ObjectInformatieObjectTypes.zaak
            )
        ),
        field_name="canonical__objectinformatieobject__zaak",
    )

    ordering = OrderingFilter(
        help_text=mark_experimental("sort on."),
        fields=(
            "auteur",
            "bestandsomvang",
            "bestandstype",
            "creatiedatum",
            "status",
            "titel",
            "vertrouwelijkheidaanduiding",
        ),
    )

    expand = ExpandFilter(serializer_class=EnkelvoudigInformatieObjectSerializer)

    class Meta:
        model = EnkelvoudigInformatieObject
        fields = (
            "creatiedatum__gte",
            "creatiedatum__lte",
            "auteur",
            "beschrijving",
            "bronorganisatie",
            "identificatie",
            "locked",
            "titel",
            "trefwoorden",
            "vertrouwelijkheidaanduiding",
            "zaak",
        )

    def locked_filter(self, queryset, name, value):
        if value:
            return queryset.exclude(canonical__lock__exact="")
        return queryset.filter(canonical__lock__exact="")


class EnkelvoudigInformatieObjectDetailFilter(FilterSet):
    versie = filters.NumberFilter(field_name="versie")
    registratie_op = filters.IsoDateTimeFilter(
        field_name="begin_registratie", lookup_expr="lte", label="begin_registratie"
    )
    expand = ExpandFilter(serializer_class=EnkelvoudigInformatieObjectSerializer)


class GebruiksrechtenFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text("documenten.Gebruiksrechten", "informatieobject"),
    )
    expand = ExpandFilter(serializer_class=GebruiksrechtenSerializer)

    class Meta:
        model = Gebruiksrechten
        fields = {
            "informatieobject": ["exact"],
            "startdatum": ["lt", "lte", "gt", "gte"],
            "einddatum": ["lt", "lte", "gt", "gte"],
        }


class GebruiksrechtenDetailFilter(FilterSet):
    expand = ExpandFilter(serializer_class=GebruiksrechtenSerializer)


class ObjectFilter(FkOrUrlFieldFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        if check_path(value, "besluiten"):
            self.field_name = "besluit"
        elif check_path(value, "zaken"):
            self.field_name = "zaak"
        elif check_path(value, "verzoeken"):
            # `verzoek` is simply a URLField (alias to _object_url)
            return qs.filter(verzoek=value)
        else:
            logger.debug(
                "Could not determine object type for URL %s, "
                "filtering to empty result set.",
                value,
            )
            return qs.none()

        return super().filter(qs, value)


class ObjectInformatieObjectFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text(
            "documenten.ObjectInformatieObject", "informatieobject"
        ),
    )
    object = ObjectFilter(
        queryset=ObjectInformatieObject.objects.all(),
        help_text=_(
            "URL-referentie naar het gerelateerde OBJECT (in deze of een andere API)."
        ),
    )

    class Meta:
        model = ObjectInformatieObject
        fields = ("object", "informatieobject")

    def filter_queryset(self, queryset):
        if settings.CMIS_ENABLED and self.data.get("informatieobject") is not None:
            # The cleaned value for informatieobject needs to be reset since a url_to_pk function
            # makes its value None when CMIS is enabled (as the eio object has no PK).
            self.form.cleaned_data["informatieobject"] = self.data["informatieobject"]
            qs = super().filter_queryset(queryset)
            # Refresh queryset
            qs._result_cache = None
            return qs
        return super().filter_queryset(queryset)


class VerzendingFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text("documenten.Verzending", "informatieobject"),
    )
    expand = ExpandFilter(serializer_class=VerzendingSerializer)

    class Meta:
        model = Verzending
        fields = {
            "aard_relatie": ["exact"],
            "informatieobject": ["exact"],
            "betrokkene": ["exact"],
        }


class VerzendingDetailFilter(FilterSet):
    expand = ExpandFilter(serializer_class=VerzendingSerializer)
