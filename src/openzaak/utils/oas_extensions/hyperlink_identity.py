# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.utils.translation import gettext_lazy as _

from drf_spectacular.extensions import OpenApiSerializerFieldExtension


class HyperlinkedIdentityFieldExtension(OpenApiSerializerFieldExtension):
    target_class = "rest_framework.relations.HyperlinkedIdentityField"
    match_subclasses = True

    def map_serializer_field(self, auto_schema, direction):
        default_schema = auto_schema._map_serializer_field(
            self.target, direction, bypass_extensions=True
        )

        return {
            **default_schema,
            "description": _(
                "URL-referentie naar dit object. Dit is de unieke "
                "identificatie en locatie van dit object."
            ),
            "minLength": 1,
            "maxLength": 1000,
        }
