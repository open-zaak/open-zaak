# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.plumbing import ResolvedComponent
from drf_spectacular.settings import spectacular_settings
from vng_api_common.utils import underscore_to_camel


class PolymorphicSerializerExtension(OpenApiSerializerExtension):
    target_class = "vng_api_common.polymorphism.PolymorphicSerializer"
    match_subclasses = True

    def map_serializer(self, auto_schema, direction):
        if not getattr(self.target, "discriminator", None):
            raise AttributeError(
                "'PolymorphicSerializer' derived serializers need to have 'discriminator' set"
            )

        discriminator = self.target.discriminator

        # resolve component with base path
        base_schema = auto_schema._map_serializer(
            self.target, direction, bypass_extensions=True
        )
        base_name = f"Base_{self.target.__class__.__name__}"
        if direction == "request" and spectacular_settings.COMPONENT_SPLIT_REQUEST:
            base_name = base_name + "Request"
        base_component = ResolvedComponent(
            name=base_name,
            type=ResolvedComponent.SCHEMA,
            object=base_name,
            schema=base_schema,
        )
        auto_schema.registry.register_on_missing(base_component)

        components = {}
        # resolve sub components and components
        for resource_type, sub_serializer in discriminator.mapping.items():
            if not sub_serializer or not sub_serializer.fields:
                schema = {"allOf": [base_component.ref]}
            else:
                sub_component = auto_schema.resolve_serializer(
                    sub_serializer, direction
                )
                schema = {"allOf": [base_component.ref, sub_component.ref]}

            component_name = f"{resource_type.value}_{self.target.__class__.__name__}"
            if direction == "request" and spectacular_settings.COMPONENT_SPLIT_REQUEST:
                component_name = component_name + "Request"
            component = ResolvedComponent(
                name=component_name,
                type=ResolvedComponent.SCHEMA,
                object=component_name,
                schema=schema,
            )
            auto_schema.registry.register_on_missing(component)

            components[resource_type.value] = component

        return {
            "oneOf": [component.ref for _, component in components.items()],
            "discriminator": {
                "propertyName": underscore_to_camel(discriminator.discriminator_field),
                "mapping": {
                    resource: component.ref["$ref"]
                    for resource, component in components.items()
                },
            },
        }
