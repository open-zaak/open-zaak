# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import build_basic_type
from drf_spectacular.types import OpenApiTypes


class EnkelvoudigInformatieObjectFieldExtension(OpenApiSerializerFieldExtension):
    target_class = (
        "openzaak.components.documenten.api.fields.EnkelvoudigInformatieObjectField"
    )

    def map_serializer_field(self, auto_schema, direction):
        schema = build_basic_type(OpenApiTypes.URI)
        if direction == "response":
            schema["nullable"] = True
        return schema
