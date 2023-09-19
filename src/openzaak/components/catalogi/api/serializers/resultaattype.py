# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ZaakobjectTypes,
)
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)
from vng_api_common.utils import get_help_text

from openzaak.utils.validators import ResourceValidator, UniqueTogetherValidator

from ...models import ResultaatType
from ..validators import (
    BrondatumArchiefprocedureValidator,
    ProcestermijnAfleidingswijzeValidator,
    ProcesTypeValidator,
    ZaakTypeConceptValidator,
)


class BrondatumArchiefprocedureSerializer(GegevensGroepSerializer):
    class Meta:
        model = ResultaatType
        gegevensgroep = "brondatum_archiefprocedure"

        extra_kwargs = {"procestermijn": {"allow_null": True}}

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(Afleidingswijze)
        fields["afleidingswijze"].help_text += "\n\n{}".format(value_display_mapping)

        value_display_mapping = add_choice_values_help_text(ZaakobjectTypes)
        fields["objecttype"].help_text += "\n\n{}".format(value_display_mapping)

        return fields


class ResultaatTypeSerializer(
    NestedGegevensGroepMixin, serializers.HyperlinkedModelSerializer
):

    brondatum_archiefprocedure = BrondatumArchiefprocedureSerializer(
        label=_("Brondatum archiefprocedure"),
        required=False,
        allow_null=True,
        help_text=(
            "Specificatie voor het bepalen van de brondatum voor de "
            "start van de Archiefactietermijn (=brondatum) van het zaakdossier."
        ),
    )
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

    class Meta:
        model = ResultaatType
        fields = (
            "url",
            "zaaktype",
            "zaaktype_identificatie",
            "omschrijving",
            "resultaattypeomschrijving",
            "omschrijving_generiek",
            "selectielijstklasse",
            "toelichting",
            "archiefnominatie",
            "archiefactietermijn",
            "brondatum_archiefprocedure",
            "catalogus",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "resultaattypeomschrijving": {
                "validators": [
                    ResourceValidator(
                        "ResultaattypeOmschrijvingGeneriek",
                        settings.REFERENTIELIJSTEN_API_STANDARD,
                    )
                ]
            },
            "omschrijving_generiek": {
                "read_only": True,
                "help_text": _(
                    "Waarde van de omschrijving-generiek referentie (attribuut `omschrijving`)"
                ),
            },
            "zaaktype": {"lookup_field": "uuid", "label": _("is van")},
            "selectielijstklasse": {
                "validators": [
                    ResourceValidator("Resultaat", settings.SELECTIELIJST_API_STANDARD)
                ]
            },
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ResultaatType.objects.all(),
                fields=["zaaktype", "omschrijving"],
            ),
            ProcesTypeValidator("selectielijstklasse"),
            ProcestermijnAfleidingswijzeValidator("selectielijstklasse"),
            BrondatumArchiefprocedureValidator(),
            ZaakTypeConceptValidator(),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        fields["archiefnominatie"].help_text += "\n\n{}".format(value_display_mapping)

        return fields
