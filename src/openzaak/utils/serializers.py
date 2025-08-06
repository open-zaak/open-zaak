# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Any

from rest_framework import fields as drf_fields, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import Serializer


class ConvertNoneMixin:
    """
    Convert None values to the empty-value field type.

    DRF skips the :meth:`rest_framework.fields.Field.to_representation` call if the
    value of the instance is ``None``. However, fields can be not-nullable (indicated
    by ``allow_null=False``), which means the value must be converted to the empty value
    for that particular field type.
    """

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        fields = self._readable_fields

        for field in fields:
            if representation[field.field_name] is not None:
                continue

            if field.allow_null:
                continue

            if isinstance(field, drf_fields.CharField):
                representation[field.field_name] = ""

        return representation


def get_from_serializer_data_or_instance(
    field: str, data: dict, serializer: Serializer
) -> Any:
    serializer_field = serializer.fields[field]
    # TODO: this won't work with source="*" or nested references
    data_value = data.get(serializer_field.source, drf_fields.empty)
    if data_value is not drf_fields.empty:
        return data_value

    instance = serializer.instance
    if not instance:
        return None

    return serializer_field.get_attribute(instance)


class SubSerializerMixin:
    """
    Sub serializers should only validate if they themselves have a value if required, further sub serializer field validation is done later.
    """

    def run_validation(self, data=empty):
        (is_empty_value, data) = self.validate_empty_values(data)
        return data


class ConvenienceSerializer(serializers.Serializer):
    def _handle_errors(self, index=None, **errors):
        found_errors = {}
        for prefix, error_list in errors.items():
            found_errors |= {
                f"{prefix}.{k}" if index is None else f"{prefix}.{index}.{k}": v
                for k, v in error_list.items()
            }

        if found_errors:
            raise ValidationError(found_errors)
