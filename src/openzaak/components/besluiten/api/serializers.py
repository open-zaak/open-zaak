"""
Serializers of the Besluit Registratie Component REST API
"""
from django.conf import settings

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import IsImmutableValidator, validate_rsin

from openzaak.utils.validators import (
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
    PublishValidator,
)

from ..constants import VervalRedenen
from ..models import Besluit, BesluitInformatieObject
from .validators import (
    BesluittypeInformatieobjecttypeRelationValidator,
    BesluittypeZaaktypeValidator,
    UniekeIdentificatieValidator,
)
from openzaak.components.documenten.api.fields import EnkelvoudigInformatieObjectField


class BesluitSerializer(serializers.HyperlinkedModelSerializer):
    vervalreden_weergave = serializers.CharField(
        source="get_vervalreden_display", read_only=True
    )

    class Meta:
        model = Besluit
        fields = (
            "url",
            "identificatie",
            "verantwoordelijke_organisatie",
            "besluittype",
            "zaak",
            "datum",
            "toelichting",
            "bestuursorgaan",
            "ingangsdatum",
            "vervaldatum",
            "vervalreden",
            "vervalreden_weergave",
            "publicatiedatum",
            "verzenddatum",
            "uiterlijke_reactiedatum",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            # per BRC API spec!
            "besluittype": {
                "lookup_field": "uuid",
                "max_length": 200,
                "validators": [
                    LooseFkResourceValidator("BesluitType", settings.ZTC_API_SPEC),
                    LooseFkIsImmutableValidator(),
                    PublishValidator(),
                ],
            },
            # per BRC API spec!
            "zaak": {"lookup_field": "uuid", "max_length": 200},
            "identificatie": {"validators": [IsImmutableValidator()]},
            "verantwoordelijke_organisatie": {
                "validators": [IsImmutableValidator(), validate_rsin]
            },
        }
        validators = [UniekeIdentificatieValidator(), BesluittypeZaaktypeValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(VervalRedenen)
        self.fields["vervalreden"].help_text += f"\n\n{value_display_mapping}"


class BesluitInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectField(
        validators=[
            LooseFkIsImmutableValidator(instance_path="canonical"),
            LooseFkResourceValidator(
                "EnkelvoudigInformatieObject", settings.DRC_API_SPEC
            ),
        ],
        max_length=1000,
        min_length=1,
    )

    class Meta:
        model = BesluitInformatieObject
        fields = ("url", "informatieobject", "besluit")
        validators = [
            UniqueTogetherValidator(
                queryset=BesluitInformatieObject.objects.all(),
                fields=["besluit", "informatieobject"],
            ),
            BesluittypeInformatieobjecttypeRelationValidator(),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "besluit": {"lookup_field": "uuid", "validators": [IsImmutableValidator()]},
        }
