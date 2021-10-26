# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.utils.encoding import force_str

from django_filters import filters
from rest_framework.filters import OrderingFilter

from rest_framework.compat import coreapi, coreschema
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.search import is_search_view


class MaximaleVertrouwelijkheidaanduidingFilter(filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("choices", VertrouwelijkheidsAanduiding.choices)
        kwargs.setdefault("lookup_expr", "lte")
        super().__init__(*args, **kwargs)

        # rewrite the field_name correctly
        self._field_name = self.field_name
        self.field_name = f"_{self._field_name}_order"

    def filter(self, qs, value):
        if value in filters.EMPTY_VALUES:
            return qs
        order_expression = VertrouwelijkheidsAanduiding.get_order_expression(
            self._field_name
        )
        qs = qs.annotate(**{self.field_name: order_expression})
        numeric_value = VertrouwelijkheidsAanduiding.get_choice(value).order
        return super().filter(qs, numeric_value)


class SearchOrderingFilter(OrderingFilter):
    """
    Ordering filter compatible with search views.

    The search views have their parameters in the request body, while the default
    ordering filter only looks up parameters in the query params.
    """

    def get_ordering(self, request, queryset, view):
        # for search views, look up the parameters from the body
        if is_search_view(view):
            params = request.data.get(self.ordering_param)
            if params:
                fields = [param.strip() for param in params.split(",")]
                ordering = self.remove_invalid_fields(queryset, fields, view, request)
                if ordering:
                    return ordering
        return super().get_ordering(request, queryset, view)

    def get_schema_fields(self, view):
        """
        Display as enum in schema, to show which fields can be used
        for ordering
        """
        assert (
            coreapi is not None
        ), "coreapi must be installed to use `get_schema_fields()`"
        assert (
            coreschema is not None
        ), "coreschema must be installed to use `get_schema_fields()`"
        return [
            coreapi.Field(
                name=self.ordering_param,
                required=False,
                location="query",
                schema=coreschema.Enum(
                    title=force_str(self.ordering_title),
                    description=force_str(self.ordering_description),
                    enum=view.ordering_fields,
                ),
            )
        ]
