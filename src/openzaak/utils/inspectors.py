# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from collections import OrderedDict
from typing import Iterable

from django.conf import settings

from drf_yasg import openapi
from drf_yasg.inspectors.base import NotHandled
from drf_yasg.inspectors.field import FieldInspector, SerializerInspector

from openzaak.utils.inclusion import get_component_name, get_include_resources

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


API_VERSION_MAPPING = {
    "autorisaties": settings.AUTORISATIES_API_VERSION,
    "besluiten": settings.BESLUITEN_API_VERSION,
    "catalogi": settings.CATALOGI_API_VERSION,
    "documenten": settings.DOCUMENTEN_API_VERSION,
    "zaken": settings.ZAKEN_API_VERSION,
}


def get_schema_ref(component: str, resource: str, current_component: str) -> str:
    """
    Constructs the schema reference for internal and external resources
    """
    schema_ref = f"#/components/schemas/{resource}"
    if current_component != component:
        ref_url = f"{settings.COMPONENT_TO_API_SPEC_MAPPING[component]}{schema_ref}"
        return ref_url.format(
            component=component,
            version=API_VERSION_MAPPING[component],
            schema_ref=schema_ref,
        )
    return schema_ref


class IncludeSerializerInspector(SerializerInspector):
    def get_inclusion_props(self, serializer_class) -> OrderedDict:
        inclusion_props = OrderedDict()
        inclusion_opts = get_include_resources(serializer_class)
        for component, resource in inclusion_opts:
            ref_url = get_schema_ref(
                component, resource, get_component_name(serializer_class)
            )
            inclusion_props[f"{component}:{resource}".lower()] = openapi.Schema(
                type=openapi.TYPE_ARRAY, items=openapi.SwaggerDict(**{"$ref": ref_url}),
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
                properties["inclusions"] = openapi.Schema(
                    type=openapi.TYPE_OBJECT, properties=inclusion_props
                )

                schema = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=properties,
                    required=response["schema"].get("required", []) + ["inclusions"],
                )
                response["schema"] = schema

        return response_schema
