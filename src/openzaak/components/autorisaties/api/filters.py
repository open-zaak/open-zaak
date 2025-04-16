# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.filtersets import FilterSet

from openzaak.utils.filters import CharArrayFilter


class ApplicatieFilter(FilterSet):
    client_ids = CharArrayFilter(field_name="client_ids", lookup_expr="contains")

    class Meta:
        model = Applicatie
        fields = ("client_ids",)


class ApplicatieRetrieveFilter(FilterSet):
    client_id = CharArrayFilter(
        field_name="client_ids",
        lookup_expr="contains",
        required=True,
        help_text=_("Geef het client ID op waarvoor je de applicatie wil opvragen."),
    )

    class Meta:
        model = Applicatie
        fields = ("client_id",)
