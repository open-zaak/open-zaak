# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
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
from vng_api_common.validators import ResourceValidator

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(Afleidingswijze)
        self.fields["afleidingswijze"].help_text += "\n\n{}".format(
            value_display_mapping
        )

        value_display_mapping = add_choice_values_help_text(ZaakobjectTypes)
        self.fields["objecttype"].help_text += "\n\n{}".format(value_display_mapping)


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

    class Meta:
        model = ResultaatType
        fields = (
            "url",
            "zaaktype",
            "omschrijving",
            "resultaattypeomschrijving",
            "omschrijving_generiek",
            "selectielijstklasse",
            "toelichting",
            "archiefnominatie",
            "archiefactietermijn",
            "brondatum_archiefprocedure",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "resultaattypeomschrijving": {
                "validators": [
                    ResourceValidator(
                        "ResultaattypeOmschrijvingGeneriek",
                        settings.REFERENTIELIJSTEN_API_SPEC,
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
                    ResourceValidator("Resultaat", settings.REFERENTIELIJSTEN_API_SPEC)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        self.fields["archiefnominatie"].help_text += "\n\n{}".format(
            value_display_mapping
        )
