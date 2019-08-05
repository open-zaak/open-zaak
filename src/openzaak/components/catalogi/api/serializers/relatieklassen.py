from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from ...models.choices import RichtingChoices
from ...models import ZaakInformatieobjectType


class ZaakTypeInformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Represent a ZaakTypeInformatieObjectType.

    Relatie met informatieobjecttype dat relevant is voor zaaktype.
    """
    class Meta:
        model = ZaakInformatieobjectType
        fields = (
            'url',
            'zaaktype',
            'informatieobjecttype',
            'volgnummer',
            'richting',
            'statustype',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid'
            },
            'zaaktype': {
                'lookup_field': 'uuid'
            },
            'informatieobjecttype': {
                'lookup_field': 'uuid'
            },
            'statustype': {
                'lookup_field': 'uuid'
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        self.fields['richting'].help_text += f"\n\n{value_display_mapping}"



# class ZaakInformatieobjectTypeArchiefregimeSerializer(FlexFieldsSerializerMixin, SourceMappingSerializerMixin,
#                                                       NestedHyperlinkedModelSerializer):
#     """
#     RSTIOTARC-basis
#
#     Afwijkende archiveringskenmerken van informatieobjecten van een INFORMATIEOBJECTTYPE bij zaken van een ZAAKTYPE op
#     grond van resultaten van een RESULTAATTYPE bij dat ZAAKTYPE.
#     """
#     parent_lookup_kwargs = {
#         'catalogus_pk': 'zaak_informatieobject_type__zaaktype__catalogus__pk',
#         'zaaktype_pk': 'zaak_informatieobject_type__zaaktype__pk',
#     }
#
#     gerelateerde = NestedHyperlinkedRelatedField(
#         read_only=True,
#         source='zaak_informatieobject_type',
#         view_name='api:informatieobjecttype-detail',
#         parent_lookup_kwargs={
#             'catalogus_pk': 'informatieobjecttype__catalogus__pk',
#             'pk': 'informatieobjecttype__pk'
#         },
#     )
#
#     class Meta:
#         model = ZaakInformatieobjectTypeArchiefregime
#         ref_name = model.__name__
#         source_mapping = {
#             'rstzdt.selectielijstklasse': 'selectielijstklasse',
#             'rstzdt.archiefnominatie': 'archiefnominatie',
#             'rstzdt.archiefactietermijn': 'archiefactietermijn',
#         }
#
#         fields = (
#             'url',
#             'gerelateerde',
#             'rstzdt.selectielijstklasse',
#             'rstzdt.archiefnominatie',
#             'rstzdt.archiefactietermijn',
#         )
#         extra_kwargs = {
#             'url': {'view_name': 'api:rstiotarc-detail'},
#         }
