# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from collections import OrderedDict
from typing import Iterable

from drf_yasg import openapi
from drf_yasg.inspectors.base import NotHandled
from drf_yasg.inspectors.field import FieldInspector, SerializerInspector

from openzaak.utils.inclusion import get_include_options_for_serializer

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


class IncludeSerializerInspector(SerializerInspector):
    def get_inclusion_props(self, serializer_class) -> OrderedDict:
        inclusion_props = OrderedDict()
        inclusion_opts = get_include_options_for_serializer(
            serializer_class, namespacing=True
        )
        # TODO use reference?
        for key, serializer in inclusion_opts:
            inclusion_props[key] = openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}),
            )

        return inclusion_props

    def get_inclusion_responses(
        self, renderer_classes: Iterable, response_schema: OrderedDict
    ) -> OrderedDict:
        for status, response in response_schema.items():
            if "schema" not in response:
                continue

            inclusion_props = self.get_inclusion_props(self.view.serializer_class)
            if "properties" in response["schema"]:
                properties = response["schema"]["properties"]
                properties["data"] = properties.pop("results")
                properties["inclusions"] = openapi.Schema(
                    type=openapi.TYPE_OBJECT, properties=inclusion_props
                )

                schema = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=properties,
                    required=response["schema"].get("required", ["data", "inclusions"]),
                )
            else:
                schema = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=OrderedDict(
                        (
                            ("data", response["schema"]),
                            (
                                "inclusions",
                                openapi.Schema(
                                    type=openapi.TYPE_OBJECT, properties=inclusion_props
                                ),
                            ),
                        )
                    ),
                    required=response["schema"].get("required", ["data", "inclusions"]),
                )

            response["schema"] = schema

        return response_schema
