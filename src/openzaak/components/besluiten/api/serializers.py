"""
Serializers of the Besluit Registratie Component REST API
"""
from django.conf import settings

from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import (
    IsImmutableValidator, ResourceValidator, validate_rsin
)

from openzaak.components.besluiten.models.constants import VervalRedenen
from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject
from openzaak.components.besluiten.sync.signals import SyncError

from .auth import get_drc_auth, get_zrc_auth, get_ztc_auth
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
            'zaak': {
                'validators': [
                    ResourceValidator(
                        'Zaak',
                        settings.ZRC_API_SPEC,
                        get_auth=get_zrc_auth,
                        headers={'Accept-Crs': 'EPSG:4326'}
                    )
                ]
            },
            'besluittype': {
                'validators': [
                    ResourceValidator('BesluitType', settings.ZTC_API_SPEC, get_auth=get_ztc_auth)
                ],
            },
        }
        validators = [
            UniekeIdentificatieValidator(),
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
            UniqueTogetherValidator(
                queryset=BesluitInformatieObject.objects.all(),
                fields=['besluit', 'informatieobject']
            ),
            ZaaktypeInformatieobjecttypeRelationValidator("informatieobject"),
        ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid'
            },
            'informatieobject': {
                'validators': [
                    ResourceValidator('EnkelvoudigInformatieObject', settings.DRC_API_SPEC, get_auth=get_drc_auth),
                    IsImmutableValidator(),
                ]
            },
            'besluit': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()]
            }
        }

    def save(self, **kwargs):
        # can't slap a transaction atomic on this, since ZRC/BRC query for the
        # relation!
        try:
            return super().save(**kwargs)
        except SyncError as sync_error:
            # delete the object again
            BesluitInformatieObject.objects.filter(
                informatieobject=self.validated_data['informatieobject'],
                besluit=self.validated_data['besluit']
            )._raw_delete('default')
            raise serializers.ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: sync_error.args[0]
            }) from sync_error
