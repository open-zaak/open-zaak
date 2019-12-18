from rest_framework import serializers

from openzaak.components.catalogi.models import Catalogus, ZaakType


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


class CatalogusSerializer(serializers.ModelSerializer):
    zaaktypen = ZaakTypeSerializer(source="zaaktype_set", many=True, read_only=True)

    class Meta:
        model = Catalogus
        fields = (
            "id",
            "_admin_name",
            "uuid",
            "domein",
            "zaaktypen",
        )
