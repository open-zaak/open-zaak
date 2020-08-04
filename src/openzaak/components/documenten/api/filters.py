# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import re
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django_filters import rest_framework as filters
from django_loose_fk.filters import FkOrUrlFieldFilter
from vng_api_common.filters import URLModelChoiceFilter
from vng_api_common.filtersets import FilterSet
from vng_api_common.utils import get_help_text

from ..models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)

logger = logging.getLogger(__name__)


class EnkelvoudigInformatieObjectListFilter(FilterSet):
    class Meta:
        model = EnkelvoudigInformatieObject
        fields = ("identificatie", "bronorganisatie")


class EnkelvoudigInformatieObjectDetailFilter(FilterSet):
    versie = filters.NumberFilter(field_name="versie")
    registratie_op = filters.IsoDateTimeFilter(
        field_name="begin_registratie", lookup_expr="lte", label="begin_registratie"
    )


class GebruiksrechtenFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text("documenten.Gebruiksrechten", "informatieobject"),
    )

    class Meta:
        model = Gebruiksrechten
        fields = {
            "informatieobject": ["exact"],
            "startdatum": ["lt", "lte", "gt", "gte"],
            "einddatum": ["lt", "lte", "gt", "gte"],
        }


def check_path(url, resource):
    # get_viewset_for_path can't be used since the external url can contain different subpathes
    path = urlparse(url).path
    # check general structure
    pattern = r".*/{}/(.+)".format(resource)
    match = re.match(pattern, path)
    if not match:
        return False

    # check uuid
    resource_id = match.group(1)
    try:
        uuid.UUID(resource_id)
    except ValueError:
        return False

    return True


class ObjectFilter(FkOrUrlFieldFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        if check_path(value, "besluiten"):
            self.field_name = "besluit"
        elif check_path(value, "zaken"):
            self.field_name = "zaak"
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
