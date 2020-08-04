# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.utils import get_help_text

from ...models import BesluitType, InformatieObjectType, ZaakType
from ..validators import (
    ConceptUpdateValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
    RelationCatalogValidator,
)


class BesluitTypeSerializer(serializers.HyperlinkedModelSerializer):
    informatieobjecttypen = serializers.HyperlinkedRelatedField(
        view_name="informatieobjecttype-detail",
        many=True,
        lookup_field="uuid",
        queryset=InformatieObjectType.objects.all(),
        help_text=get_help_text("catalogi.BesluitType", "informatieobjecttypen"),
    )

    zaaktypen = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="zaaktype-detail",
        lookup_field="uuid",
        queryset=ZaakType.objects.all(),
        help_text=get_help_text("catalogi.BesluitType", "zaaktypen"),
    )

    class Meta:
        model = BesluitType
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
            "zaaktypen",
            "omschrijving",
            "omschrijving_generiek",
            "besluitcategorie",
            "reactietermijn",
            "publicatie_indicatie",
            "publicatietekst",
            "publicatietermijn",
            "toelichting",
            "informatieobjecttypen",
            "begin_geldigheid",
            "einde_geldigheid",
            "concept",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=BesluitType.objects.all(), fields=["catalogus", "omschrijving"]
            ),
            RelationCatalogValidator("informatieobjecttypen"),
            RelationCatalogValidator("zaaktypen"),
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["zaaktypen", "informatieobjecttypen"]),
            M2MConceptUpdateValidator(["zaaktypen", "informatieobjecttypen"]),
        ]
