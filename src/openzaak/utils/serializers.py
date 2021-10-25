# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.module_loading import import_string

from rest_framework import fields as drf_fields
from rest_framework_nested.serializers import NestedHyperlinkedRelatedField


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


class ExpandSerializer(NestedHyperlinkedRelatedField):
    def __init__(self, *args, **kwargs):
        # For some reason self.field_name is empty for `many=True`
        self.name = kwargs.pop("name")

        self.default_serializer = kwargs.pop("default_serializer")
        self.expanded_serializer = kwargs.pop("expanded_serializer")

        self.default_serializer_kwargs = kwargs.pop("default_serializer_kwargs", {})
        self.expanded_serializer_kwargs = kwargs.pop("expanded_serializer_kwargs", {})

        # Update the serializer specific kwargs with the kwargs used for all
        # serializers
        common_kwargs = kwargs.pop("common_kwargs")
        self.default_serializer_kwargs.update(common_kwargs)
        self.expanded_serializer_kwargs.update(common_kwargs)

        kwargs.update(self.default_serializer_kwargs)

        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        serializer_class = self.default_serializer
        if isinstance(self.default_serializer, str):
            serializer_class = import_string(self.default_serializer)
        serializer = serializer_class(**self.default_serializer_kwargs)
        serializer.parent = self

        if hasattr(self.context["request"], "query_params"):
            expand = self.context["request"].query_params.getlist("expand")
            if self.name in expand:
                serializer_class = self.expanded_serializer
                if isinstance(self.expanded_serializer, str):
                    serializer_class = import_string(self.expanded_serializer)
                serializer = serializer_class(**self.expanded_serializer_kwargs)
                serializer.parent = self

        if self.default_serializer_kwargs.get("many", False):
            value = value.all()

        return serializer.to_representation(value)
