# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.plumbing import build_array_type


class ObjectOrArraySerializerExtension(OpenApiSerializerExtension):
    """
    Changes the response schema to be an object or array.
    """

    def map_serializer(self, auto_schema, direction):
        object_schema = auto_schema._map_serializer(
            self.target, direction, bypass_extensions=True
        )
        array_schema = build_array_type(object_schema)

        if direction == "request":
            return object_schema

        return {
            "oneOf": [
                object_schema,
                array_schema,
            ]
        }


class ReservedDocumentSerializerExtension(ObjectOrArraySerializerExtension):
    target_class = (
        "openzaak.components.documenten.api.serializers.ReservedDocumentSerializer"
    )
