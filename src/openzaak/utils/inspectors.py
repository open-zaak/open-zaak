# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from drf_yasg import openapi
from drf_yasg.inspectors.base import NotHandled
from drf_yasg.inspectors.field import FieldInspector, ReferencingSerializerInspector
from rest_framework.serializers import Serializer

from .expansion import EXPAND_KEY
from .serializer_fields import LengthHyperlinkedRelatedField

logger = logging.getLogger(__name__)


class LengthHyperlinkedRelatedFieldInspector(FieldInspector):
    def field_to_swagger_object(
        self, field, swagger_object_type, use_references, **kwargs
    ):
        SwaggerType, ChildSwaggerType = self._get_partial_types(
            field, swagger_object_type, use_references, **kwargs
        )

        if (
            isinstance(field, LengthHyperlinkedRelatedField)
            and swagger_object_type == openapi.Schema
        ):
            max_length = getattr(field, "max_length", None)
            min_length = getattr(field, "min_length", None)
            res = SwaggerType(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_URI,
                min_length=min_length,
                max_length=max_length,
            )

            return res

        return NotHandled


class ExpandSerializerInspector(ReferencingSerializerInspector):
    def field_to_swagger_object(
        self,
        field: Serializer,
        swagger_object_type,
        use_references: bool,
        inside_inclusion: bool = False,
        **kwargs,
    ):
        include_allowed = getattr(self.view, "include_allowed", lambda: False)()
        inclusion_serializers = getattr(field, "inclusion_serializers", {})

        if not include_allowed or not inclusion_serializers or inside_inclusion:
            return NotHandled

        # retrieve base schema
        base_schema_ref = super().field_to_swagger_object(
            field, swagger_object_type, use_references, **kwargs
        )

        # create schema for inclusions
        expand_properties = {}
        for name, serializer_class in inclusion_serializers.items():
            # create schema for top-level inclusions for now
            if "." in name:
                continue

            # todo is it array or not
            inclusion_serializer = import_string(serializer_class)()
            inclusion_ref = self.probe_field_inspectors(
                inclusion_serializer,
                openapi.Schema,
                use_references=True,
                inside_inclusion=True,
            )
            expand_properties[name] = inclusion_ref

        expand_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=expand_properties,
            description=_(
                "Display details of the linked resources requested in the `expand` parameter"
            ),
        )

        # combine base schema with inclusions
        allof_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            all_of=[
                base_schema_ref,
                openapi.Schema(
                    type=openapi.TYPE_OBJECT, properties={EXPAND_KEY: expand_schema},
                ),
            ],
        )

        return allof_schema
