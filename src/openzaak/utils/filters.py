# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from django_filters import filters
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from .expansion import get_expand_options_for_serializer


class CharArrayFilter(filters.BaseInFilter, filters.CharFilter):
    pass


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


class ExpandFilter(filters.BaseInFilter, filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        serializer_class = kwargs.pop("serializer_class")

        kwargs.setdefault(
            "choices", get_expand_options_for_serializer(serializer_class)
        )
        kwargs.setdefault(
            "help_text",
            _("Sluit de gespecifieerde gerelateerde resources in in het antwoord. "),
        )

        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        return qs
