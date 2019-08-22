from rest_framework import serializers
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import add_choice_values_help_text

from ...models import InformatieObjectType


class InformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer based on ``IOT-basis`` specified in XSD ``ztc0310_ent_basis.xsd``.
    """

    # This is needed because spanning relations is not done correctly when specifying the ``source`` attribute later,
    # as is done by the ``Meta.source_mapping`` property.
    # omschrijvingGeneriek = serializers.CharField(
    #     read_only=True,
    #     source='informatieobjecttype_omschrijving_generiek.informatieobjecttype_omschrijving_generiek',
    #     max_length=80,
    #     help_text=_('Algemeen gehanteerde omschrijving van het type informatieobject.')
    # )
    #
    # isVastleggingVoor = NestedHyperlinkedRelatedField(
    #     many=True,
    #     read_only=True,
    #     source='besluittype_set',
    #     view_name='api:besluittype-detail',
    #     parent_lookup_kwargs={'catalogus_pk': 'catalogus__pk'}
    # )
    # isRelevantVoor = NestedHyperlinkedRelatedField(
    #     many=True,
    #     read_only=True,
    #     source='zaakinformatieobjecttype_set',
    #     view_name='api:zktiot-detail',
    #     parent_lookup_kwargs={
    #         'catalogus_pk': 'zaaktype__catalogus__pk',
    #         'zaaktype_pk': 'zaaktype__pk',
    #     }
    # )

    class Meta:
        model = InformatieObjectType
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "catalogus": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
            "concept": {"read_only": True},
        }
        fields = (
            "url",
            "catalogus",
            "omschrijving",
            "vertrouwelijkheidaanduiding",
            "begin_geldigheid",
            "einde_geldigheid",
            "concept",
            # 'omschrijvingGeneriek',
            # 'categorie',
            # 'trefwoord',
            # 'vertrouwelijkAanduiding',
            # 'model',
            # 'toelichting',
            # 'ingangsdatumObject',
            # 'einddatumObject',
            # 'isRelevantVoor',
            # 'isVastleggingVoor',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        self.fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"
