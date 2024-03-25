# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.text import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.utils import get_help_text

from ...models import BesluitType, InformatieObjectType
from ..validators import (
    ConceptUpdateValidator,
    GeldigheidPublishValidator,
    GeldigheidValidator,
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
        read_only=True,
        help_text=get_help_text("catalogi.BesluitType", "zaaktypen"),
    )

    resultaattypen = serializers.HyperlinkedRelatedField(
        many=True,
        source="resultaattype_set",
        view_name="resultaattype-detail",
        lookup_field="uuid",
        read_only=True,
        help_text=_(
            "Het RESULTAATTYPE van resultaten die gepaard gaan met besluiten"
            " van het BESLUITTYPE."
        ),
    )
    resultaattypen_omschrijving = serializers.SlugRelatedField(
        many=True,
        source="resultaattype_set",
        read_only=True,
        slug_field="omschrijving",
        help_text=_("Omschrijving van de aard van resultaten van het RESULTAATTYPE."),
    )

    vastgelegd_in = serializers.SlugRelatedField(
        many=True,
        source="informatieobjecttypen",
        read_only=True,
        slug_field="omschrijving",
        help_text=_(
            "Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    begin_object = serializers.DateField(
        read_only=True,
        help_text=_("De datum waarop de eerst versie van het object ontstaan is."),
    )
    einde_object = serializers.DateField(
        read_only=True,
        help_text=_("De datum van de aller laatste versie van het object."),
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
            "resultaattypen",
            "resultaattypen_omschrijving",
            "vastgelegd_in",
            "begin_object",
            "einde_object",
        )
        validators = [
            GeldigheidValidator(),
            RelationCatalogValidator("informatieobjecttypen"),
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["informatieobjecttypen"]),
            M2MConceptUpdateValidator(["informatieobjecttypen"]),
        ]


class BesluitTypePublishSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BesluitType
        fields = ("concept",)
        validators = [
            GeldigheidPublishValidator(),
        ]
