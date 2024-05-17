# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import fields as drf_fields, serializers

from openzaak.utils.models import Import, ImportStatusChoices


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
    field: str, data: dict, serializer: serializers.Serializer
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


class ImportSerializer(serializers.HyperlinkedModelSerializer):
    status = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, instance):
        status = ImportStatusChoices(instance.status)
        return status.label

    class Meta:
        model = Import
        fields = (
            "total",
            "processed",
            "processed_successfully",
            "processed_invalid",
            "status",
        )


class ImportCreateSerializer(serializers.HyperlinkedModelSerializer):
    upload_url = serializers.SerializerMethodField()
    status_url = serializers.SerializerMethodField()
    report_url = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_upload_url(self, instance):
        return instance.get_upload_url()

    @extend_schema_field(OpenApiTypes.URI)
    def get_status_url(self, instance):
        return instance.get_status_url()

    @extend_schema_field(OpenApiTypes.URI)
    def get_report_url(self, instance):
        return instance.get_report_url()

    class Meta:
        model = Import
        read_only_fields = (
            "upload_url",
            "status_url",
            "report_url",
        )

        fields = read_only_fields
