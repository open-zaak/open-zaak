"""
Serializers of the Besluit Registratie Component REST API
"""
from openzaak.components.besluiten.models import (
    Besluit, BesluitInformatieObject
)
from openzaak.components.besluiten.models.constants import VervalRedenen
from openzaak.components.documenten.api.serializers import EnkelvoudigInformatieObjectHyperlinkedRelatedField
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from rest_framework import serializers
from vng_api_common.utils import get_help_text
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import (
    IsImmutableValidator, validate_rsin
)

from .validators import (
    BesluittypeZaaktypeValidator, UniekeIdentificatieValidator,
    ZaaktypeInformatieobjecttypeRelationValidator
)


class BesluitSerializer(serializers.HyperlinkedModelSerializer):
    vervalreden_weergave = serializers.CharField(source='get_vervalreden_display', read_only=True)

    class Meta:
        model = Besluit
        fields = (
            'url',
            'identificatie',
            'verantwoordelijke_organisatie',
            'besluittype',
            'zaak',
            'datum',
            'toelichting',
            'bestuursorgaan',
            'ingangsdatum',
            'vervaldatum',
            'vervalreden',
            'vervalreden_weergave',
            'publicatiedatum',
            'verzenddatum',
            'uiterlijke_reactiedatum',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'identificatie': {
                'validators': [IsImmutableValidator()],
            },
            'verantwoordelijke_organisatie': {
                'validators': [IsImmutableValidator(), validate_rsin],
            },
            'besluittype': {
                'lookup_field': 'uuid',
            },
            'zaak': {
                'lookup_field': 'uuid',
            }
        }
        validators = [
            UniekeIdentificatieValidator(),
            # BesluittypeZaaktypeValidator()
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(VervalRedenen)
        self.fields['vervalreden'].help_text += f"\n\n{value_display_mapping}"


class BesluitInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name='enkelvoudiginformatieobject-detail',
        lookup_field='uuid',
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text('documenten.Gebruiksrechten', 'informatieobject'),
        validators=[IsImmutableValidator()]
    )

    class Meta:
        model = BesluitInformatieObject
        fields = (
            'url',
            'informatieobject',
            'besluit',
        )
        # validators = [
        #     ZaaktypeInformatieobjecttypeRelationValidator(),
        #     TODO check unique together in testcases
        # ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid'
            },
            'besluit': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()]
            }
        }
