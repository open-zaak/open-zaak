# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django_filters import OrderingFilter as _OrderingFilter, constants
from vng_api_common.filtersets import FilterSet as _FilterSet


class FilterSet(_FilterSet):
    """
    Add help texts for model field filters
    """

    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        filter = super().filter_for_field(field, field_name, lookup_expr)

        if not filter.extra.get("help_text"):
            filter.extra["help_text"] = getattr(field, "help_text", None)
        return filter


class OrderingFilter(_OrderingFilter):
    def filter(self, qs, value):
        if value in constants.EMPTY_VALUES:
            return qs

        ordering = [self.get_ordering_value(param) for param in value]
        return qs.order_by(*ordering).distinct()
