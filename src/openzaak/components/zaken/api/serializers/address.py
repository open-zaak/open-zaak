# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from rest_framework import serializers

from ...models import Adres

logger = logging.getLogger(__name__)


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
            "aoa_identificatie": {"source": "identificatie"},
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


class TerreinGebouwdObjectAdresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adres
        fields = (
            "num_identificatie",
            "oao_identificatie",
            "wpl_woonplaats_naam",
            "gor_openbare_ruimte_naam",
            "aoa_postcode",
            "aoa_huisnummer",
            "aoa_huisletter",
            "aoa_huisnummertoevoeging",
            "ogo_locatie_aanduiding",
        )
        extra_kwargs = {
            "oao_identificatie": {"source": "identificatie"},
            "aoa_postcode": {"source": "postcode"},
            "aoa_huisnummer": {"source": "huisnummer"},
            "aoa_huisletter": {"source": "huisletter"},
            "aoa_huisnummertoevoeging": {"source": "huisnummertoevoeging"},
            "ogo_locatie_aanduiding": {"source": "locatie_aanduiding"},
        }
