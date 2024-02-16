# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.utils.translation import gettext as _

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import build_basic_type
from drf_spectacular.types import OpenApiTypes


class Base64FileFileFieldExtension(OpenApiSerializerFieldExtension):
    target_class = "drf_extra_fields.fields.Base64FileField"
    match_subclasses = True

    def map_serializer_field(self, auto_schema, direction):
        base64_schema = {
            **build_basic_type(OpenApiTypes.BYTE),
            "description": _("Base64 encoded binary content."),
        }

        uri_schema = {
            **build_basic_type(OpenApiTypes.URI),
            "description": _("Download URL of the binary content."),
        }

        if direction == "request":
            return base64_schema
        elif direction == "response":
            return uri_schema if not self.target.represent_in_base64 else base64_schema
