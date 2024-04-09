# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from urllib.parse import urlparse

from django.db.models import Q

from django_loose_fk.filters import FkOrUrlFieldFilter
from django_loose_fk.utils import get_resource_for_path
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


# Updated FkOrUrlFieldFilter for nested model field filtering
class NestedFkOrUrlFieldFilter(FkOrUrlFieldFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        values = value
        if not isinstance(values, list):
            values = [values]

        parsed_values = [urlparse(value) for value in values]
        host = self.parent.request.get_host()

        # Updated the retrieval of the model field so it is done recursively.
        model_field_list = self.field_name.split("__")
        assert len(model_field_list) > 1
        model_field = self.model._meta.get_field(model_field_list.pop(0))
        for field_name in model_field_list:
            model_field = model_field.target_field.model._meta.get_field(field_name)

        filters = self.get_filters(model_field, parsed_values, host)

        complex_filter = Q()
        for lookup, value in filters.items():
            complex_filter |= Q(**{lookup: value})

        try:
            qs = self.get_method(self.queryset)(complex_filter) or self.get_method(qs)(
                complex_filter
            )
        except ValueError:
            return self.queryset.none() or qs.none()
        return qs.distinct() if self.distinct else qs

    def get_filters(self, model_field, parsed_values, host) -> dict:
        # Updated local and external filter key strings to get the full paths.
        model_field_path = self.field_name.rsplit("__", 1)[0]
        local_filter_key = (
            f"{model_field_path}__{model_field.fk_field}__{self.lookup_expr}"
        )
        external_filter_key = (
            f"{model_field_path}__{model_field.url_field}__{self.lookup_expr}"
        )

        filters = {}
        for value in parsed_values:
            local = value.netloc == host
            if local:
                local_object = get_resource_for_path(value.path)
                if self.instance_path:
                    for bit in self.instance_path.split("."):
                        local_object = getattr(local_object, bit)
                filter_key = local_filter_key
                filter_value = local_object
            else:
                filter_key = external_filter_key
                filter_value = value.geturl()

            if self.lookup_expr == "in":
                if filter_key in filters:
                    filters[filter_key] += [filter_value]
                else:
                    filters[filter_key] = [filter_value]
            elif self.lookup_expr == "exact":
                filters[filter_key] = filter_value

        return filters
