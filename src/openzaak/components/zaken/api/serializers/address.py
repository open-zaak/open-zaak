# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

import structlog
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from ...models import Adres

logger = structlog.stdlib.get_logger(__name__)


class ObjectAdresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adres
        fields = (
            "identificatie",
            "wpl_woonplaats_naam",
            "gor_openbare_ruimte_naam",
            "huisnummer",
            "huisletter",
            "huisnummertoevoeging",
            "postcode",
        )


class VerblijfsAdresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adres
        fields = (
            "aoa_identificatie",
            "wpl_woonplaats_naam",
            "gor_openbare_ruimte_naam",
            "aoa_postcode",
            "aoa_huisnummer",
            "aoa_huisletter",
            "aoa_huisnummertoevoeging",
            "inp_locatiebeschrijving",
        )
        extra_kwargs = {
            "aoa_identificatie": {"source": "identificatie", "required": True},
            "aoa_postcode": {"source": "postcode"},
            "aoa_huisnummer": {"source": "huisnummer"},
            "aoa_huisletter": {"source": "huisletter"},
            "aoa_huisnummertoevoeging": {"source": "huisnummertoevoeging"},
            "inp_locatiebeschrijving": {"source": "locatie_omschrijving"},
        }


class WozObjectAdresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adres
        fields = (
            "aoa_identificatie",
            "wpl_woonplaats_naam",
            "gor_openbare_ruimte_naam",
            "aoa_postcode",
            "aoa_huisnummer",
            "aoa_huisletter",
            "aoa_huisnummertoevoeging",
            "locatie_omschrijving",
        )
        extra_kwargs = {
            "aoa_identificatie": {"source": "identificatie"},
            "aoa_postcode": {"source": "postcode"},
            "aoa_huisnummer": {"source": "huisnummer"},
            "aoa_huisletter": {"source": "huisletter"},
            "aoa_huisnummertoevoeging": {"source": "huisnummertoevoeging"},
        }


@extend_schema_serializer(deprecate_fields="oao_identificatie")
class TerreinGebouwdObjectAdresSerializer(serializers.ModelSerializer):
    oao_identificatie = serializers.CharField(
        source="identificatie",
        required=False,
        help_text=_(
            "Dit veld is verkeerd gespeld en is daarom deprecated. "
            "Het wordt vervangen door `aoaIdentificatie`. "
            "Als `aoaIdentificatie` nog niet wordt gebruikt dan is dit "
            "veld nog steeds verplicht voor backwards compatibility."
        ),
    )

    aoa_identificatie = serializers.CharField(
        source="identificatie",
        required=False,
        help_text=_(
            "De unieke identificatie van het OBJECT. "
            "Als `oaoIdentificatie` niet meer wordt gebruikt dan is dit veld verplicht."
        ),
    )

    class Meta:
        model = Adres
        fields = (
            "num_identificatie",
            "oao_identificatie",
            "aoa_identificatie",
            "wpl_woonplaats_naam",
            "gor_openbare_ruimte_naam",
            "aoa_postcode",
            "aoa_huisnummer",
            "aoa_huisletter",
            "aoa_huisnummertoevoeging",
            "ogo_locatie_aanduiding",
        )
        extra_kwargs = {
            "aoa_postcode": {"source": "postcode"},
            "aoa_huisnummer": {"source": "huisnummer"},
            "aoa_huisletter": {"source": "huisletter"},
            "aoa_huisnummertoevoeging": {"source": "huisnummertoevoeging"},
            "ogo_locatie_aanduiding": {"source": "locatie_aanduiding"},
        }

    def to_internal_value(self, data):
        oao_field = "oao_identificatie" in data
        aoa_field = "aoa_identificatie" in data

        if oao_field and aoa_field:
            raise serializers.ValidationError(
                {
                    "aoaIdentificatie": _(
                        "Geef `oaoIdentificatie` of `aoaIdentificatie` op, "
                        "maar niet beide."
                    )
                }
            )

        if not self.instance and not oao_field and not aoa_field:
            raise serializers.ValidationError(
                {
                    "aoaIdentificatie": _(
                        "Geef `aoaIdentificatie` op als `oaoIdentificatie` "
                        "niet is opgegeven."
                    )
                }
            )

        return super().to_internal_value(data)
