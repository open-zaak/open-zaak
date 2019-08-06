"""
Serializers of the Besluit Registratie Component REST API
"""
from django.conf import settings

from openzaak.components.besluiten.models import (
    Besluit, BesluitInformatieObject
)
from openzaak.components.besluiten.models.constants import VervalRedenen
from openzaak.components.besluiten.sync.signals import SyncError
from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import (
    IsImmutableValidator, validate_rsin
)

from openzaak.utils.auth import get_auth
from openzaak.utils.validators import ResourceValidator
from .validators import (
    BesluittypeZaaktypeValidator, ZaaktypeInformatieobjecttypeRelationValidator
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
            'zaak': {
                'validators': [
                    ResourceValidator(
                        'Zaak',
                        settings.ZRC_API_SPEC,
                        get_auth=get_auth,
                        headers={'Accept-Crs': 'EPSG:4326'}
                    )
                ]
            },
            'besluittype': {
                'validators': [
                    ResourceValidator(
                        'BesluitType',
                        settings.ZTC_API_SPEC,
                        get_auth=get_auth
                    )
                ],
            },
        }
        validators = [
            # UniekeIdentificatieValidator(), # this checi is on DB level
            BesluittypeZaaktypeValidator('besluittype')
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(VervalRedenen)
        self.fields['vervalreden'].help_text += f"\n\n{value_display_mapping}"

    def create(self, validated_data):
        zaak = validated_data.pop('zaak', '')
        besluit = super().create(validated_data)
        try:
            besluit.zaak = zaak
            besluit.save()
        except SyncError as sync_error:
            besluit.delete()
            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: sync_error.args[0]},
                code='sync-with-zrc'
            ) from sync_error
        else:
            return besluit


class BesluitInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BesluitInformatieObject
        fields = (
            'url',
            'informatieobject',
            'besluit',
        )
        validators = [
            # UniqueTogetherValidator(
            #     queryset=BesluitInformatieObject.objects.all(),
            #     fields=['besluit', 'informatieobject']
            # ),
            ZaaktypeInformatieobjecttypeRelationValidator("informatieobject"),
        ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid'
            },
            'informatieobject': {
                'validators': [
                    ResourceValidator('EnkelvoudigInformatieObject', settings.DRC_API_SPEC, get_auth=get_auth),
                    IsImmutableValidator(),
                ]
            },
            'besluit': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()]
            }
        }

    def create(self, validated_data):
        informatieobject = validated_data.pop('informatieobject', '')
        bio = super().create(validated_data)
        try:
            bio.informatieobject = informatieobject
            bio.save()
        except SyncError as sync_error:
            bio.delete()
            raise serializers.ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: sync_error.args[0]
            }) from sync_error
        else:
            return bio
