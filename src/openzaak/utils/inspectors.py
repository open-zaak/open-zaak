# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from drf_yasg import openapi
from drf_yasg.inspectors.base import NotHandled
from drf_yasg.inspectors.field import FieldInspector
from drf_yasg.inspectors.query import DjangoRestResponsePagination

from .apidoc import mark_oas_difference
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


class FuzzyPaginationInspector(DjangoRestResponsePagination):
    def get_paginated_response(self, paginator, response_schema):
        from .pagination import FuzzyPagination

        paged_schema = super().get_paginated_response(paginator, response_schema)

        if not isinstance(paginator, FuzzyPagination):
            return paged_schema

        paged_schema.properties["countExact"] = openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            x_nullable=True,
            description=mark_oas_difference(
                "Geeft aan of de `count` exact is, of dat deze wegens "
                "performance doeleinden niet exact berekend is."
            ),
        )

        return paged_schema
