import logging

from django_loose_fk.drf import FKOrURLField
from drf_yasg import openapi
from drf_yasg.inspectors.base import NotHandled
from drf_yasg.inspectors.field import FieldInspector

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


class LooseFkFieldInspector(FieldInspector):
    def field_to_swagger_object(
        self, field, swagger_object_type, use_references, **kwargs
    ):
        SwaggerType, ChildSwaggerType = self._get_partial_types(
            field, swagger_object_type, use_references, **kwargs
        )

        if isinstance(field, FKOrURLField) and swagger_object_type == openapi.Schema:
            max_length = getattr(field, "max_length", None)
            min_length = getattr(field, "min_length", None)

            params = {
                "type": openapi.TYPE_STRING,
                "format": openapi.FORMAT_URI,
                "min_length": min_length,
                "max_length": max_length,
            }

            res = SwaggerType(**params)

            # remove x-nullable = True from schema for loose-fk
            res.pop("x-nullable", None)

            return res

        return NotHandled
