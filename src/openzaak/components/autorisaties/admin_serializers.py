# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import serializers

from openzaak.components.catalogi.models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakType,
)


class ZaakTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZaakType
        fields = (
            "id",
            "uuid",
            "identificatie",
            "omschrijving",
            "concept",
            "versiedatum",
        )
        extra_kwargs = {"omschrijving": {"source": "zaaktype_omschrijving",}}


class InformatieObjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "id",
            "uuid",
            "omschrijving",
            "concept",
        )


class BesluitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BesluitType
        fields = (
            "id",
            "uuid",
            "omschrijving",
            "concept",
        )


class CatalogusSerializer(serializers.ModelSerializer):
    zaaktypen = ZaakTypeSerializer(source="zaaktype_set", many=True, read_only=True)
    informatieobjecttypen = InformatieObjectTypeSerializer(
        source="informatieobjecttype_set", many=True, read_only=True,
    )
    besluittypen = BesluitTypeSerializer(
        source="besluittype_set", many=True, read_only=True,
    )

    class Meta:
        model = Catalogus
        fields = (
            "id",
            "_admin_name",
            "uuid",
            "domein",
            "zaaktypen",
            "informatieobjecttypen",
            "besluittypen",
        )
