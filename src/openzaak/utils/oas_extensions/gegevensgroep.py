# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from drf_spectacular.extensions import OpenApiSerializerExtension


class GegevensGroepSerializerExtension(OpenApiSerializerExtension):
    target_class = "vng_api_common.serializers.GegevensGroepSerializer"
    match_subclasses = True

    def map_serializer(self, auto_schema, direction) -> dict:
        schema = auto_schema._map_serializer(
            self.target, direction, bypass_extensions=True
        )

        # remove description because it uses GegevensGroepSerializer docstring
        # the parent serializer will add a description from help text for this component
        del schema["description"]

        return schema
