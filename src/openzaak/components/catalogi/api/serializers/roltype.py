# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from drf_writable_nested import NestedCreateMixin
from rest_framework import serializers
from vng_api_common.constants import RolOmschrijving
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.utils import get_help_text

from ...models import RolType
from ..validators import StartBeforeEndValidator, ZaakTypeConceptValidator


class RolTypeSerializer(NestedCreateMixin, serializers.HyperlinkedModelSerializer):
    catalogus = serializers.HyperlinkedRelatedField(
        view_name="catalogus-detail",
        source="zaaktype.catalogus",
        read_only=True,
        lookup_field="uuid",
        help_text=get_help_text("catalogi.ZaakType", "catalogus"),
    )
    zaaktype_identificatie = serializers.SlugRelatedField(
        source="zaaktype",
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
    )
    begin_object = serializers.DateField(
        source="datum_begin_geldigheid",
        read_only=True,
        help_text=_("De datum waarop de eerst versie van het object ontstaan is."),
    )
    einde_object = serializers.DateField(
        source="datum_einde_geldigheid",
        read_only=True,
        help_text=_("De datum van de aller laatste versie van het object."),
    )

    class Meta:
        model = RolType
        fields = (
            "url",
            "zaaktype",
            "zaaktype_identificatie",
            "omschrijving",
            "omschrijving_generiek",
            "catalogus",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "zaaktype": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
        }
        validators = [ZaakTypeConceptValidator(), StartBeforeEndValidator()]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(RolOmschrijving)
        fields["omschrijving_generiek"].help_text += f"\n\n{value_display_mapping}"

        return fields
