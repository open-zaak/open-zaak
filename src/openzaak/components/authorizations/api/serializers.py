import logging

from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from vng_api_common.constants import ComponentTypes
from vng_api_common.polymorphism import Discriminator, PolymorphicSerializer
from vng_api_common.serializers import add_choice_values_help_text
from ..models import Applicatie, Autorisatie
from .validators import UniqueClientIDValidator

logger = logging.getLogger(__name__)


class AutorisatieBaseSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field='component',
        mapping={
            ComponentTypes.zrc: (
                'zaaktype',
                'max_vertrouwelijkheidaanduiding',
            ),
            ComponentTypes.drc: (
                'informatieobjecttype',
                'max_vertrouwelijkheidaanduiding',
            ),
            ComponentTypes.brc: (
                'besluittype',
            ),
        }
    )

    component_weergave = serializers.CharField(source='get_component_display', read_only=True)

    class Meta:
        model = Autorisatie
        fields = (
            'component',
            'component_weergave',
            'scopes',
        )
        extra_kwargs = {
            'scopes': {
                'help_text': _(
                    "Lijst van scope labels. Elke scope geeft toegang tot een "
                    "set van acties/operaties, zoals gedocumenteerd bij de "
                    "betreffende component."
                ),
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(ComponentTypes)
        self.fields['component'].help_text += f"\n\n{value_display_mapping}"


class ApplicatieSerializer(serializers.HyperlinkedModelSerializer):
    autorisaties = AutorisatieBaseSerializer(many=True, required=False)

    class Meta:
        model = Applicatie
        fields = (
            'url',
            'client_ids',
            'label',
            'heeft_alle_autorisaties',
            'autorisaties'
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'heeft_alle_autorisaties': {
                'required': False,
            },
            'client_ids': {
                'validators': [UniqueClientIDValidator()],
                'help_text': _("Lijst van consumer identifiers (hun 'client_id'). Een "
                               "`client_id` mag slechts bij één applicatie-object voorkomen."),
            }
        }

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        # either autorisaties or heeft_alle_autorisaties can be specified
        autorisaties_obj = None
        heeft_alle_autorisaties_obj = None
        # in case of update:
        if self.instance:
            autorisaties_obj = self.instance.autorisaties.all()
            heeft_alle_autorisaties_obj = self.instance.heeft_alle_autorisaties

        autorisaties = validated_attrs.get('autorisaties', autorisaties_obj)
        heeft_alle_autorisaties = validated_attrs.get('heeft_alle_autorisaties', heeft_alle_autorisaties_obj)

        if autorisaties and heeft_alle_autorisaties is True:
            raise serializers.ValidationError(
                _('Either autorisaties or heeft_alle_autorisaties can be specified'),
                code='ambiguous-authorizations-specified')

        if not autorisaties and heeft_alle_autorisaties is not True:
            raise serializers.ValidationError(
                _('Either autorisaties or heeft_alle_autorisaties should be specified'),
                code='missing-authorizations')

        return validated_attrs

    @transaction.atomic
    def create(self, validated_data):
        autorisaties_data = validated_data.pop('autorisaties', None)
        applicatie = super().create(validated_data)

        if autorisaties_data:
            for auth in autorisaties_data:
                Autorisatie.objects.create(**auth, applicatie=applicatie)

        return applicatie

    @transaction.atomic
    def update(self, instance, validated_data):
        autorisaties_data = validated_data.pop('autorisaties', None)
        applicatie = super().update(instance, validated_data)

        # in case of update autorisaties - remove all related autorisaties
        if autorisaties_data:
            applicatie.autorisaties.all().delete()
            for auth in autorisaties_data:
                Autorisatie.objects.create(**auth, applicatie=applicatie)

        return applicatie
