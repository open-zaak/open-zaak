# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)

from ...models import InformatieObjectType
from ..validators import (
    ConceptUpdateValidator,
    GeldigheidValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
)


class OmschrijvingGeneriekSerializer(GegevensGroepSerializer):
    class Meta:
        model = InformatieObjectType
        gegevensgroep = "omschrijving_generiek"


class InformatieObjectTypeSerializer(
    NestedGegevensGroepMixin, serializers.HyperlinkedModelSerializer
):
    omschrijving_generiek = OmschrijvingGeneriekSerializer(
        required=False,
        help_text=_("Algemeen gehanteerde omschrijving van het informatieobjecttype."),
    )

    class Meta:
        model = InformatieObjectType
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "catalogus": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
            "concept": {"read_only": True},
            "besluittypen": {
                "lookup_field": "uuid",
                "read_only": True,
                "many": True,
                "help_text": _("URL-referenties naar de BESLUITTYPEN"),
            },
        }
        fields = (
            "url",
            "catalogus",
            "omschrijving",
            "vertrouwelijkheidaanduiding",
            "begin_geldigheid",
            "einde_geldigheid",
            "concept",
            "besluittypen",
            "trefwoord",
            "omschrijving_generiek",
        )
        validators = [
            GeldigheidValidator(),
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["besluittypen", "zaaktypen"]),
            M2MConceptUpdateValidator(["besluittypen", "zaaktypen"]),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"

        return fields
