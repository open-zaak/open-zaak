# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import fields as drf_fields


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
