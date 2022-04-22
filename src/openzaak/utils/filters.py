# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import List, Optional

from django.utils.module_loading import import_string


from django_filters import filters
from rest_framework.serializers import Serializer
from vng_api_common.constants import VertrouwelijkheidsAanduiding


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
        numeric_value = VertrouwelijkheidsAanduiding.get_choice_order(value)
        return super().filter(qs, numeric_value)


def get_include_choices_for_serializer(
    dotted_path: str, serializer_class: Serializer, result: Optional[List[tuple]] = None
) -> List[tuple]:
    """
    Determine the possible choices for the `include` query parameter given a serializer
    """
    if not result:
        result = []

    if not hasattr(serializer_class, "inclusion_serializers"):
        return result

    for field, inclusion_serializer in serializer_class.inclusion_serializers.items():
        key = f"{dotted_path}.{field}" if dotted_path else field
        result.append((key, key))
        return get_include_choices_for_serializer(
            field, import_string(inclusion_serializer), result
        )


class IncludeFilter(filters.BaseInFilter, filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        serializer_class = kwargs.pop("serializer_class")

        choices = get_include_choices_for_serializer("", serializer_class)
        choices.append(("*", "*",))
        kwargs.setdefault("choices", choices)

        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        return qs
