# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import add_choice_values_help_text

from ...models import InformatieObjectType
from ..validators import (
    ConceptUpdateValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
)


class InformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InformatieObjectType
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "catalogus": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
            "concept": {"read_only": True},
        }
        fields = (
            "url",
            "catalogus",
            "omschrijving",
            "vertrouwelijkheidaanduiding",
            "begin_geldigheid",
            "einde_geldigheid",
            "concept",
        )
        validators = [
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["besluittypen", "zaaktypen"]),
            M2MConceptUpdateValidator(["besluittypen", "zaaktypen"]),
            UniqueTogetherValidator(
                queryset=InformatieObjectType.objects.all(),
                fields=["catalogus", "omschrijving"],
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        self.fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"
