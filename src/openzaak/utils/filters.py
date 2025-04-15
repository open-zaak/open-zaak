# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from django_filters import filters
from rest_framework.exceptions import ParseError
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
        # TODO use new integerfield
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


class KeyValueFilter(filters.CharFilter):

    def __init__(self, key_field_name, value_field_name, *args, **kwargs):
        validators = kwargs.get("validators", [])

        assert isinstance(validators, list), "'validators' must be of type list."

        # key:value where the key and value cannot contain `[`, `]` or `:`
        validators.append(RegexValidator(r"^([^:]+):([^:]+)$"))

        kwargs["validators"] = validators

        super().__init__(*args, **kwargs)
        self.key_field_name = key_field_name
        self.value_field_name = value_field_name

    def filter(self, qs, value):
        if value in filters.EMPTY_VALUES:
            return qs

        value_list = value.split(":")

        # This should not be possible because of the regex validator but to be sure:
        if len(value_list) != 2:  # pragma: nocover
            raise ParseError(
                _("Ongeldig format voor key-value filter.")
            )  # pragma: nocover

        key_field_value, value_field_value = value_list

        key_lookup = "%s__%s" % (self.key_field_name, self.lookup_expr)
        value_lookup = "%s__%s" % (self.value_field_name, self.lookup_expr)

        return self.get_method(qs)(
            **{key_lookup: key_field_value, value_lookup: value_field_value}
        )
