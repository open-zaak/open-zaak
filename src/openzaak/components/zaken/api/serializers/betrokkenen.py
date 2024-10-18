# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.utils.translation import gettext_lazy as _

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
from .authentication_context import (
    DigiDAuthContextSerializer,
    eHerkenningAuthContextSerializer,
)

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


class NatuurlijkPersoonIdentificatieSerializer(serializers.ModelSerializer):
    verblijfsadres = VerblijfsAdresSerializer(required=False, allow_null=True)
    sub_verblijf_buitenland = SubVerblijfBuitenlandSerializer(
        required=False, allow_null=True
    )

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(GeslachtsAanduiding)
        fields["geslachtsaanduiding"].help_text += f"\n\n{value_display_mapping}"

        return fields

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


class RolNatuurlijkPersoonSerializer(serializers.ModelSerializer):
    betrokkene_identificatie = NatuurlijkPersoonIdentificatieSerializer(required=False)
    authenticatie_context = DigiDAuthContextSerializer(
        label=_("authentication context"),
        required=False,
        allow_null=True,
        default=None,
        help_text=_(
            "Information about the authentication and mandate (if relevant) that "
            "applied when the role was added to the case. It is essential when you "
            "later want to retrieve information again which should match certain "
            "authentication guarantees, like minimum level of assurance. The exact "
            "shape of data depends on the selected `betrokkeneType`.\n\n"
            "Use `null` if unknown or when creating a role other than the `initiator`."
        ),
    )

    class Meta:
        model = NatuurlijkPersoon
        fields = (
            "betrokkene_identificatie",
            "authenticatie_context",
        )


class NietNatuurlijkPersoonIdentificatieSerializer(serializers.ModelSerializer):
    sub_verblijf_buitenland = SubVerblijfBuitenlandSerializer(
        required=False, allow_null=True
    )

    class Meta:
        model = NietNatuurlijkPersoon
        fields = (
            "inn_nnp_id",
            "ann_identificatie",
            "kvk_nummer",
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
            sub_verblijf_buitenland_data["nietnatuurlijkpersoon"] = (
                nietnatuurlijkpersoon
            )
            SubVerblijfBuitenlandSerializer().create(sub_verblijf_buitenland_data)
        return nietnatuurlijkpersoon


class RolNietNatuurlijkPersoonSerializer(serializers.ModelSerializer):
    betrokkene_identificatie = NietNatuurlijkPersoonIdentificatieSerializer(
        required=False
    )
    authenticatie_context = eHerkenningAuthContextSerializer(
        label=_("authentication context"),
        required=False,
        allow_null=True,
        default=None,
        help_text=_(
            "Information about the authentication and mandate (if relevant) that "
            "applied when the role was added to the case. It is essential when you "
            "later want to retrieve information again which should match certain "
            "authentication guarantees, like minimum level of assurance. The exact "
            "shape of data depends on the selected `betrokkeneType`.\n\n"
            "Use `null` if unknown or when creating a role other than the `initiator`."
        ),
    )

    class Meta:
        model = NietNatuurlijkPersoon
        fields = ("betrokkene_identificatie", "authenticatie_context")


class VestigingIdentificatieSerializer(serializers.ModelSerializer):
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
            "kvk_nummer",
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


class RolVestigingSerializer(serializers.ModelSerializer):
    betrokkene_identificatie = VestigingIdentificatieSerializer(required=False)
    authenticatie_context = eHerkenningAuthContextSerializer(
        label=_("authentication context"),
        required=False,
        allow_null=True,
        default=None,
        help_text=_(
            "Information about the authentication and mandate (if relevant) that "
            "applied when the role was added to the case. It is essential when you "
            "later want to retrieve information again which should match certain "
            "authentication guarantees, like minimum level of assurance. The exact "
            "shape of data depends on the selected `betrokkeneType`.\n\n"
            "Use `null` if unknown or when creating a role other than the `initiator`."
        ),
    )

    class Meta:
        model = Vestiging
        fields = ("betrokkene_identificatie", "authenticatie_context")


class OrganisatorischeEenheidIdentificatieSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisatorischeEenheid
        fields = ("identificatie", "naam", "is_gehuisvest_in")


class RolOrganisatorischeEenheidSerializer(serializers.ModelSerializer):
    betrokkene_identificatie = OrganisatorischeEenheidIdentificatieSerializer(
        required=False
    )

    class Meta:
        model = OrganisatorischeEenheid
        fields = ("betrokkene_identificatie",)


class MedewerkerIdentificatieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medewerker
        fields = (
            "identificatie",
            "achternaam",
            "voorletters",
            "voorvoegsel_achternaam",
        )


class RolMedewerkerSerializer(serializers.ModelSerializer):
    betrokkene_identificatie = MedewerkerIdentificatieSerializer(required=False)

    class Meta:
        model = Medewerker
        fields = ("betrokkene_identificatie",)
