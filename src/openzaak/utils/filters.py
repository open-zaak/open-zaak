# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.utils.encoding import force_str

from django_filters import filters
from rest_framework import filters as drf_filters
from rest_framework.compat import coreapi, coreschema
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.utils.apidoc import mark_oas_difference


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


# TODO move to vng-api-common
class OrderingFilter(drf_filters.OrderingFilter):
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
                    description=force_str(
                        mark_oas_difference(self.ordering_description)
                    ),
                    enum=view.ordering_fields,
                ),
            )
        ]


# TODO move to vng-api-common
class ExpandFilter(filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        serializer_class = kwargs.pop("serializer_class")
        kwargs.setdefault(
            "choices", [(x, x) for x in serializer_class.Meta.expandable_fields]
        )

        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        return qs
