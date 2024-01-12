# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from drf_spectacular.extensions import OpenApiSerializerFieldExtension


class FKOrURLFieldFieldExtension(OpenApiSerializerFieldExtension):
    target_class = "openzaak.utils.serializer_fields.FKOrServiceUrlField"
    match_subclasses = True

    def map_serializer_field(self, auto_schema, direction):
        default_schema = auto_schema._map_serializer_field(
            self.target, direction, bypass_extensions=True
        )

        return {
            **default_schema,
            "type": "string",
            "format": "uri",
            "minLength": self.target.min_length,
            "maxLength": self.target.max_length,
        }
