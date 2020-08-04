# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from ...constants import GeslachtsAanduiding
from ...models import (
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    SubVerblijfBuitenland,
    Vestiging,
)
from .address import VerblijfsAdresSerializer

logger = logging.getLogger(__name__)


class SubVerblijfBuitenlandSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubVerblijfBuitenland
        fields = (
            "lnd_landcode",
            "lnd_landnaam",
            "sub_adres_buitenland_1",
            "sub_adres_buitenland_2",
            "sub_adres_buitenland_3",
        )


class RolNatuurlijkPersoonSerializer(serializers.ModelSerializer):
    verblijfsadres = VerblijfsAdresSerializer(required=False, allow_null=True)
    sub_verblijf_buitenland = SubVerblijfBuitenlandSerializer(
        required=False, allow_null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(GeslachtsAanduiding)
        self.fields["geslachtsaanduiding"].help_text += f"\n\n{value_display_mapping}"

    class Meta:
        model = NatuurlijkPersoon
        fields = (
            "inp_bsn",
            "anp_identificatie",
            "inp_a_nummer",
            "geslachtsnaam",
            "voorvoegsel_geslachtsnaam",
            "voorletters",
            "voornamen",
            "geslachtsaanduiding",
            "geboortedatum",
            "verblijfsadres",
            "sub_verblijf_buitenland",
        )

    def create(self, validated_data):
        verblijfsadres_data = validated_data.pop("verblijfsadres", None)
        sub_verblijf_buitenland_data = validated_data.pop(
            "sub_verblijf_buitenland", None
        )
        natuurlijkpersoon = super().create(validated_data)

        if verblijfsadres_data:
            verblijfsadres_data["natuurlijkpersoon"] = natuurlijkpersoon
            VerblijfsAdresSerializer().create(verblijfsadres_data)

        if sub_verblijf_buitenland_data:
            sub_verblijf_buitenland_data["natuurlijkpersoon"] = natuurlijkpersoon
            SubVerblijfBuitenlandSerializer().create(sub_verblijf_buitenland_data)
        return natuurlijkpersoon


class RolNietNatuurlijkPersoonSerializer(serializers.ModelSerializer):
    sub_verblijf_buitenland = SubVerblijfBuitenlandSerializer(
        required=False, allow_null=True
    )

    class Meta:
        model = NietNatuurlijkPersoon
        fields = (
            "inn_nnp_id",
            "ann_identificatie",
            "statutaire_naam",
            "inn_rechtsvorm",
            "bezoekadres",
            "sub_verblijf_buitenland",
        )

    def create(self, validated_data):
        sub_verblijf_buitenland_data = validated_data.pop(
            "sub_verblijf_buitenland", None
        )
        nietnatuurlijkpersoon = super().create(validated_data)

        if sub_verblijf_buitenland_data:
            sub_verblijf_buitenland_data[
                "nietnatuurlijkpersoon"
            ] = nietnatuurlijkpersoon
            SubVerblijfBuitenlandSerializer().create(sub_verblijf_buitenland_data)
        return nietnatuurlijkpersoon


class RolVestigingSerializer(serializers.ModelSerializer):
    verblijfsadres = VerblijfsAdresSerializer(required=False, allow_null=True)
    sub_verblijf_buitenland = SubVerblijfBuitenlandSerializer(
        required=False, allow_null=True
    )

    class Meta:
        model = Vestiging
        fields = (
            "vestigings_nummer",
            "handelsnaam",
            "verblijfsadres",
            "sub_verblijf_buitenland",
        )

    def create(self, validated_data):
        verblijfsadres_data = validated_data.pop("verblijfsadres", None)
        sub_verblijf_buitenland_data = validated_data.pop(
            "sub_verblijf_buitenland", None
        )
        vestiging = super().create(validated_data)

        if verblijfsadres_data:
            verblijfsadres_data["vestiging"] = vestiging
            VerblijfsAdresSerializer().create(verblijfsadres_data)

        if sub_verblijf_buitenland_data:
            sub_verblijf_buitenland_data["vestiging"] = vestiging
            SubVerblijfBuitenlandSerializer().create(sub_verblijf_buitenland_data)
        return vestiging


class RolOrganisatorischeEenheidSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisatorischeEenheid
        fields = ("identificatie", "naam", "is_gehuisvest_in")


class RolMedewerkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medewerker
        fields = (
            "identificatie",
            "achternaam",
            "voorletters",
            "voorvoegsel_achternaam",
        )
