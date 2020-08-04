# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from ...constants import (
    TyperingInrichtingselement,
    TyperingKunstwerk,
    TyperingWater,
    TypeSpoorbaan,
)
from ...models import (
    Buurt,
    Gemeente,
    GemeentelijkeOpenbareRuimte,
    Huishouden,
    Inrichtingselement,
    KadastraleOnroerendeZaak,
    Kunstwerkdeel,
    MaatschappelijkeActiviteit,
    OpenbareRuimte,
    Overige,
    Pand,
    Spoorbaandeel,
    Terreindeel,
    TerreinGebouwdObject,
    Waterdeel,
    Wegdeel,
    Wijk,
    Woonplaats,
    WozDeelobject,
    WozObject,
    WozWaarde,
    ZakelijkRecht,
    ZakelijkRechtHeeftAlsGerechtigde,
)
from .address import TerreinGebouwdObjectAdresSerializer, WozObjectAdresSerializer
from .zaken import RolNatuurlijkPersoonSerializer, RolNietNatuurlijkPersoonSerializer

logger = logging.getLogger(__name__)


class ObjectBuurtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buurt
        fields = ("buurt_code", "buurt_naam", "gem_gemeente_code", "wyk_wijk_code")


class ObjectGemeenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gemeente
        fields = ("gemeente_naam", "gemeente_code")


class ObjectGemeentelijkeOpenbareRuimteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GemeentelijkeOpenbareRuimte
        fields = ("identificatie", "openbare_ruimte_naam")


class ObjectInrichtingselementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inrichtingselement
        fields = ("type", "identificatie", "naam")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(TyperingInrichtingselement)
        self.fields["type"].help_text += f"\n\n{value_display_mapping}"


class ObjectKunstwerkdeelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kunstwerkdeel
        fields = ("type", "identificatie", "naam")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(TyperingKunstwerk)
        self.fields["type"].help_text += f"\n\n{value_display_mapping}"


class ObjectMaatschappelijkeActiviteitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaatschappelijkeActiviteit
        fields = ("kvk_nummer", "handelsnaam")


class ObjectOpenbareRuimteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenbareRuimte
        fields = ("identificatie", "wpl_woonplaats_naam", "gor_openbare_ruimte_naam")


class ObjectPandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pand
        fields = ("identificatie",)


class ObjectSpoorbaandeelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spoorbaandeel
        fields = ("type", "identificatie", "naam")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(TypeSpoorbaan)
        self.fields["type"].help_text += f"\n\n{value_display_mapping}"


class ObjectTerreindeelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terreindeel
        fields = ("type", "identificatie", "naam")


class ObjectWaterdeelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waterdeel
        fields = ("type_waterdeel", "identificatie", "naam")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(TyperingWater)
        self.fields["type_waterdeel"].help_text += f"\n\n{value_display_mapping}"


class ObjectWegdeelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wegdeel
        fields = ("type", "identificatie", "naam")


class ObjectWijkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wijk
        fields = ("wijk_code", "wijk_naam", "gem_gemeente_code")


class ObjectWoonplaatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Woonplaats
        fields = ("identificatie", "woonplaats_naam")


class ObjectTerreinGebouwdObjectSerializer(serializers.ModelSerializer):
    adres_aanduiding_grp = TerreinGebouwdObjectAdresSerializer(
        required=False, allow_null=True
    )

    class Meta:
        model = TerreinGebouwdObject
        fields = ("identificatie", "adres_aanduiding_grp")

    def create(self, validated_data):
        adres_data = validated_data.pop("adres_aanduiding_grp", None)
        terreingebouwdobject = super().create(validated_data)

        if adres_data:
            adres_data["terreingebouwdobject"] = terreingebouwdobject
            TerreinGebouwdObjectAdresSerializer().create(adres_data)
        return terreingebouwdobject


class ObjectHuishoudenSerializer(serializers.ModelSerializer):
    is_gehuisvest_in = ObjectTerreinGebouwdObjectSerializer(
        required=False, allow_null=True
    )

    class Meta:
        model = Huishouden
        fields = ("nummer", "is_gehuisvest_in")

    def create(self, validated_data):
        terrein_gebouwd_data = validated_data.pop("is_gehuisvest_in", None)
        huishouden = super().create(validated_data)

        if terrein_gebouwd_data:
            terrein_gebouwd_data["huishouden"] = huishouden
            ObjectTerreinGebouwdObjectSerializer().create(terrein_gebouwd_data)
        return huishouden


class ObjectWozObjectSerializer(serializers.ModelSerializer):
    aanduiding_woz_object = WozObjectAdresSerializer(required=False, allow_null=True)

    class Meta:
        model = WozObject
        fields = ("woz_object_nummer", "aanduiding_woz_object")

    def create(self, validated_data):
        adres_data = validated_data.pop("aanduiding_woz_object", None)
        wozobject = super().create(validated_data)

        if adres_data:
            adres_data["wozobject"] = wozobject
            WozObjectAdresSerializer().create(adres_data)
        return wozobject


class ObjectWozDeelobjectSerializer(serializers.ModelSerializer):
    is_onderdeel_van = ObjectWozObjectSerializer(required=False)

    class Meta:
        model = WozDeelobject
        fields = ("nummer_woz_deel_object", "is_onderdeel_van")

    def create(self, validated_data):
        woz_object_data = validated_data.pop("is_onderdeel_van", None)
        woz_deelobject = super().create(validated_data)

        if woz_object_data:
            woz_object_data["woz_deelobject"] = woz_deelobject
            ObjectWozObjectSerializer().create(woz_object_data)
        return woz_deelobject


class ObjectWozWaardeSerializer(serializers.ModelSerializer):
    is_voor = ObjectWozObjectSerializer(required=False)

    class Meta:
        model = WozWaarde
        fields = ("waardepeildatum", "is_voor")

    def create(self, validated_data):
        woz_object_data = validated_data.pop("is_voor", None)
        woz_warde = super().create(validated_data)

        if woz_object_data:
            woz_object_data["woz_warde"] = woz_warde
            ObjectWozObjectSerializer().create(woz_object_data)
        return woz_warde


class ObjectKadastraleOnroerendeZaakSerializer(serializers.ModelSerializer):
    class Meta:
        model = KadastraleOnroerendeZaak
        fields = ("kadastrale_identificatie", "kadastrale_aanduiding")


class ZakelijkRechtHeeftAlsGerechtigdeSerializer(serializers.ModelSerializer):
    natuurlijk_persoon = RolNatuurlijkPersoonSerializer(
        required=False, source="natuurlijkpersoon"
    )
    niet_natuurlijk_persoon = RolNietNatuurlijkPersoonSerializer(
        required=False, source="nietnatuurlijkpersoon"
    )

    class Meta:
        model = ZakelijkRechtHeeftAlsGerechtigde
        fields = ("natuurlijk_persoon", "niet_natuurlijk_persoon")

    def create(self, validated_data):
        natuurlijk_persoon_data = validated_data.pop("natuurlijkpersoon", None)
        niet_natuurlijk_persoon_data = validated_data.pop("nietnatuurlijkpersoon", None)
        heeft_als_gerechtigde = super().create(validated_data)

        if natuurlijk_persoon_data:
            natuurlijk_persoon_data[
                "zakelijk_rechtHeeft_als_gerechtigde"
            ] = heeft_als_gerechtigde
            RolNatuurlijkPersoonSerializer().create(natuurlijk_persoon_data)

        if niet_natuurlijk_persoon_data:
            niet_natuurlijk_persoon_data[
                "zakelijk_rechtHeeft_als_gerechtigde"
            ] = heeft_als_gerechtigde
            RolNietNatuurlijkPersoonSerializer().create(niet_natuurlijk_persoon_data)

        return heeft_als_gerechtigde


class ObjectZakelijkRechtSerializer(serializers.ModelSerializer):
    heeft_betrekking_op = ObjectKadastraleOnroerendeZaakSerializer(required=False)
    heeft_als_gerechtigde = ZakelijkRechtHeeftAlsGerechtigdeSerializer(required=False)

    class Meta:
        model = ZakelijkRecht
        fields = (
            "identificatie",
            "avg_aard",
            "heeft_betrekking_op",
            "heeft_als_gerechtigde",
        )

    def create(self, validated_data):
        heeft_betrekking_op_data = validated_data.pop("heeft_betrekking_op", None)
        heeft_als_gerechtigde_data = validated_data.pop("heeft_als_gerechtigde", None)
        zakelijk_recht = super().create(validated_data)

        if heeft_betrekking_op_data:
            heeft_betrekking_op_data["zakelijk_recht"] = zakelijk_recht
            ObjectKadastraleOnroerendeZaakSerializer().create(heeft_betrekking_op_data)

        if heeft_als_gerechtigde_data:
            heeft_als_gerechtigde_data["zakelijk_recht"] = zakelijk_recht
            ZakelijkRechtHeeftAlsGerechtigdeSerializer().create(
                heeft_als_gerechtigde_data
            )
        return zakelijk_recht


class ObjectOverigeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Overige
        fields = ("overige_data",)
