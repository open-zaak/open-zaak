# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import ResolvedComponent


class GeometryFieldExtension(OpenApiSerializerFieldExtension):
    target_class = "rest_framework_gis.fields.GeometryField"
    match_subclasses = True
    priority = 1

    def get_name(self):
        return "GeoJSONGeometry"

    def map_serializer_field(self, auto_schema, direction):
        geometry = ResolvedComponent(
            name="Geometry",
            type=ResolvedComponent.SCHEMA,
            object="Geometry",
            schema={
                "type": "object",
                "title": "Geometry",
                "description": "GeoJSON geometry",
                "required": ["type"],
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1"
                },
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "Point",
                            "MultiPoint",
                            "LineString",
                            "MultiLineString",
                            "Polygon",
                            "MultiPolygon",
                            "Feature",
                            "FeatureCollection",
                            "GeometryCollection",
                        ],
                        "description": "The geometry type",
                    }
                },
            },
        )
        point_2d = ResolvedComponent(
            name="Point2D",
            type=ResolvedComponent.SCHEMA,
            object="Point2D",
            schema={
                "type": "array",
                "title": "Point2D",
                "description": "A 2D point",
                "items": {"type": "number"},
                "maxItems": 2,
                "minItems": 2,
            },
        )
        point = ResolvedComponent(
            name="Point",
            type=ResolvedComponent.SCHEMA,
            object="Point",
            schema={
                "type": "object",
                "description": "GeoJSON point geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.2"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {"coordinates": point_2d.ref},
                    },
                ],
            },
        )

        multi_point = ResolvedComponent(
            name="MultiPoint",
            type=ResolvedComponent.SCHEMA,
            object="MultiPoint",
            schema={
                "type": "object",
                "description": "GeoJSON multi-point geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.3"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {
                            "coordinates": {"type": "array", "items": point_2d.ref}
                        },
                    },
                ],
            },
        )

        line_string = ResolvedComponent(
            name="LineString",
            type=ResolvedComponent.SCHEMA,
            object="LineString",
            schema={
                "type": "object",
                "description": "GeoJSON line-string geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.4"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {
                            "coordinates": {
                                "type": "array",
                                "items": point_2d.ref,
                                "minItems": 2,
                            }
                        },
                    },
                ],
            },
        )

        multi_line_string = ResolvedComponent(
            name="MultiLineString",
            type=ResolvedComponent.SCHEMA,
            object="MultiLineString",
            schema={
                "type": "object",
                "description": "GeoJSON multi-line-string geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.5"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {
                            "coordinates": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": point_2d.ref,
                                },
                            }
                        },
                    },
                ],
            },
        )

        polygon = ResolvedComponent(
            name="Polygon",
            type=ResolvedComponent.SCHEMA,
            object="Polygon",
            schema={
                "type": "object",
                "description": "GeoJSON polygon geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.6"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {
                            "coordinates": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": point_2d.ref,
                                },
                            }
                        },
                    },
                ],
            },
        )

        multi_polygon = ResolvedComponent(
            name="MultiPolygon",
            type=ResolvedComponent.SCHEMA,
            object="MultiPolygon",
            schema={
                "type": "object",
                "description": "GeoJSON multi-polygon geometry",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.7"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["coordinates"],
                        "properties": {
                            "coordinates": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": point_2d.ref,
                                    },
                                },
                            }
                        },
                    },
                ],
            },
        )

        geometry_collection = ResolvedComponent(
            name="GeometryCollection",
            type=ResolvedComponent.SCHEMA,
            object="GeometryCollection",
            schema={
                "type": "object",
                "description": "GeoJSON geometry collection",
                "externalDocs": {
                    "url": "https://tools.ietf.org/html/rfc7946#section-3.1.8"
                },
                "allOf": [
                    geometry.ref,
                    {
                        "type": "object",
                        "required": ["geometries"],
                        "properties": {
                            "geometries": {"type": "array", "items": geometry.ref}
                        },
                    },
                ],
            },
        )

        for component in [
            geometry,
            point_2d,
            point,
            multi_point,
            line_string,
            multi_line_string,
            polygon,
            multi_polygon,
            geometry_collection,
        ]:
            auto_schema.registry.register_on_missing(component)

        return {
            "title": "GeoJSONGeometry",
            "type": "object",
            "oneOf": [
                point.ref,
                multi_point.ref,
                line_string.ref,
                multi_line_string.ref,
                polygon.ref,
                multi_polygon.ref,
                geometry_collection.ref,
            ],
            "discriminator": {
                "propertyName": "type",
            },
        }
