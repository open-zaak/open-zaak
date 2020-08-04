# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django_loose_fk.filters import FkOrUrlFieldFilter
from vng_api_common.filtersets import FilterSet
from vng_api_common.utils import get_help_text

from ..models import Besluit, BesluitInformatieObject


class BesluitFilter(FilterSet):
    class Meta:
        model = Besluit
        fields = (
            "identificatie",
            "verantwoordelijke_organisatie",
            "besluittype",
            "zaak",
        )


class BesluitInformatieObjectFilter(FilterSet):
    informatieobject = FkOrUrlFieldFilter(
        queryset=BesluitInformatieObject.objects.all(),
        instance_path="canonical",
        help_text=get_help_text(
            "besluiten.BesluitInformatieObject", "informatieobject"
        ),
    )

    class Meta:
        model = BesluitInformatieObject
        fields = ("besluit", "informatieobject")
