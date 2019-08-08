from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from drf_writable_nested import NestedCreateMixin
from rest_framework.serializers import (
    HyperlinkedModelSerializer, HyperlinkedRelatedField, ModelSerializer
)
from rest_framework_nested.relations import NestedHyperlinkedRelatedField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    GegevensGroepSerializer, NestedGegevensGroepMixin,
    add_choice_values_help_text
)
from vng_api_common.validators import ResourceValidator

from ...models import (
    BesluitType, BronCatalogus, BronZaakType, Formulier, ZaakObjectType,
    ZaakType, ZaakTypenRelatie
)
from ...models.choices import AardRelatieChoices, RichtingChoices
from ..utils.serializers import SourceMappingSerializerMixin
from ..utils.validators import RelationCatalogValidator
from ..validators import ZaaktypeGeldigheidValidator


class ZaakObjectTypeSerializer(SourceMappingSerializerMixin, NestedHyperlinkedModelSerializer):
    parent_lookup_kwargs = {
        'catalogus_pk': 'is_relevant_voor__catalogus__pk',
        'zaaktype_pk': 'is_relevant_voor__pk',
    }

    isRelevantVoor = NestedHyperlinkedRelatedField(
        read_only=True,
        source='is_relevant_voor',
        view_name='api:zaaktype-detail',
        parent_lookup_kwargs={
            'catalogus_pk': 'catalogus__pk',
        }
    )

    class Meta:
        model = ZaakObjectType
        source_mapping = {
            'ingangsdatumObject': 'datum_begin_geldigheid',
            'einddatumObject': 'datum_einde_geldigheid',
            'anderObject': 'ander_objecttype',
            'relatieOmschrijving': 'relatieomschrijving',
        }
        fields = (
            'url',
            'objecttype',
            'anderObject',
            'relatieOmschrijving',
            'ingangsdatumObject',
            'einddatumObject',
            'isRelevantVoor',
            # NOTE: this field is not in the xsd
            # 'statustype',
        )
        extra_kwargs = {
            'url': {'view_name': 'api:zaakobjecttype-detail'},
        }


class FormulierSerializer(ModelSerializer):
    class Meta:
        model = Formulier
        ref_name = None  # Inline
        fields = ('naam', 'link')


class BronCatalogusSerializer(ModelSerializer):
    class Meta:
        model = BronCatalogus
        ref_name = None  # Inline
        fields = ('domein', 'rsin')


class BronZaakTypeSerializer(SourceMappingSerializerMixin, ModelSerializer):
    class Meta:
        model = BronZaakType
        ref_name = None  # Inline
        source_mapping = {
            'identificatie': 'zaaktype_identificatie',
            'omschrijving': 'zaaktype_omschrijving',
        }
        fields = (
            'identificatie',
            'omschrijving'
        )


class ReferentieProcesSerializer(GegevensGroepSerializer):
    class Meta:
        model = ZaakType
        gegevensgroep = 'referentieproces'


class ZaakTypenRelatieSerializer(ModelSerializer):
    class Meta:
        model = ZaakTypenRelatie
        fields = (
            'zaaktype',
            'aard_relatie',
            'toelichting'
        )
        extra_kwargs = {
            'zaaktype': {'source': 'gerelateerd_zaaktype'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(AardRelatieChoices)
        self.fields['aard_relatie'].help_text += f"\n\n{value_display_mapping}"


class ZaakTypeSerializer(NestedGegevensGroepMixin, NestedCreateMixin, HyperlinkedModelSerializer):

    # formulier = FormulierSerializer(many=True, read_only=True)
    referentieproces = ReferentieProcesSerializer(
        required=True, help_text=_("Het Referentieproces dat ten grondslag ligt aan dit ZAAKTYPE.")
    )
    # broncatalogus = BronCatalogusSerializer(read_only=True)
    # bronzaaktype = BronZaakTypeSerializer(read_only=True)

    # heeftRelevantZaakObjecttype = NestedHyperlinkedRelatedField(
    #     many=True,
    #     read_only=True,
    #     source='zaakobjecttype_set',
    #     view_name='api:zaakobjecttype-detail',
    #     parent_lookup_kwargs={
    #         'catalogus_pk': 'is_relevant_voor__catalogus__pk',
    #         'zaaktype_pk': 'is_relevant_voor__pk',
    #     }
    # )
    gerelateerde_zaaktypen = ZaakTypenRelatieSerializer(
        many=True, source='zaaktypenrelaties',
        help_text="De ZAAKTYPEn van zaken die relevant zijn voor zaken van dit ZAAKTYPE."
    )
    # isDeelzaaktypeVan = NestedHyperlinkedRelatedField(
    #     many=True,
    #     read_only=True,
    #     source='is_deelzaaktype_van',
    #     view_name='api:zaaktype-detail',
    #     parent_lookup_kwargs={
    #         'catalogus_pk': 'catalogus__pk'
    #     },
    # )
    informatieobjecttypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source='heeft_relevant_informatieobjecttype',
        view_name='informatieobjecttype-detail',
        lookup_field='uuid',
        help_text=_('URL-referenties naar de INFORMATIEOBJECTTYPEN die mogelijk zijn binnen dit ZAAKTYPE.')
    )

    statustypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='statustype-detail',
        lookup_field='uuid',
        help_text=_('URL-referenties naar de STATUSTYPEN die mogelijk zijn binnen dit ZAAKTYPE.')
    )

    resultaattypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='resultaattype-detail',
        lookup_field='uuid',
        help_text=_('URL-referenties naar de RESULTAATTYPEN die mogelijk zijn binnen dit ZAAKTYPE.')
    )

    eigenschappen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source='eigenschap_set',
        view_name='eigenschap-detail',
        lookup_field='uuid',
        help_text=_('URL-referenties naar de EIGENSCHAPPEN die aanwezig moeten zijn in ZAKEN van dit ZAAKTYPE.')
    )

    roltypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source='roltype_set',
        view_name='roltype-detail',
        lookup_field='uuid',
        help_text=_('URL-referenties naar de ROLTYPEN die mogelijk zijn binnen dit ZAAKTYPE.')
    )

    besluittypen = HyperlinkedRelatedField(
        many=True,
        label=_("heeft relevante besluittypen"),
        source='besluittype_set',
        view_name='besluittype-detail',
        lookup_field='uuid',
        queryset=BesluitType.objects.all(),
        help_text=_('URL-referenties naar de BESLUITTYPEN die mogelijk zijn binnen dit ZAAKTYPE.')
    )

    class Meta:
        model = ZaakType
        fields = (
            'url',
            'identificatie',
            'omschrijving',
            'omschrijving_generiek',
            'vertrouwelijkheidaanduiding',
            # 'zaakcategorie',
            'doel',
            'aanleiding',
            'toelichting',
            'indicatie_intern_of_extern',
            'handeling_initiator',
            'onderwerp',
            'handeling_behandelaar',
            'doorlooptijd',
            'servicenorm',
            'opschorting_en_aanhouding_mogelijk',
            'verlenging_mogelijk',
            'verlengingstermijn',
            'trefwoorden',
            # 'archiefclassificatiecode',
            # 'vertrouwelijkheidAanduiding',
            # 'verantwoordelijke',
            'publicatie_indicatie',
            'publicatietekst',
            'verantwoordingsrelatie',

            'producten_of_diensten',
            'selectielijst_procestype',
            # 'formulier',
            'referentieproces',
            # 'broncatalogus',
            # 'bronzaaktype',

            # 'ingangsdatumObject',
            # 'versiedatum',
            # 'einddatumObject',

            # relaties
            'catalogus',
            'statustypen',
            'resultaattypen',
            'eigenschappen',
            'informatieobjecttypen',
            'roltypen',
            'besluittypen',
            'gerelateerde_zaaktypen',
            # # 'heeftRelevantZaakObjecttype',
            # # 'isDeelzaaktypeVan',
            'begin_geldigheid',
            'einde_geldigheid',
            'versiedatum',
            'concept',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'identificatie': {
                'source': 'zaaktype_identificatie',
            },
            'omschrijving': {
                'source': 'zaaktype_omschrijving',
            },
            'omschrijving_generiek': {
                'source': 'zaaktype_omschrijving_generiek',
            },
            'catalogus': {
                'lookup_field': 'uuid',
            },
            'doorlooptijd': {
                'source': 'doorlooptijd_behandeling',
            },
            'servicenorm': {
                'source': 'servicenorm_behandeling',
            },
            'begin_geldigheid': {
                'source': 'datum_begin_geldigheid'
            },
            'einde_geldigheid': {
                'source': 'datum_einde_geldigheid'
            },
            'concept': {
                'read_only': True,
            },
            'selectielijst_procestype': {
                'validators': [ResourceValidator(
                    'ProcesType',
                    settings.REFERENTIELIJSTEN_API_SPEC
                )],
            },
        }

        # expandable_fields = {
        #     'catalogus': ('openzaak.components.catalogi.api.serializers.CatalogusSerializer', {'source': 'catalogus'}),
        # }
        validators = [
            ZaaktypeGeldigheidValidator(),
            RelationCatalogValidator('besluittype_set'),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(VertrouwelijkheidsAanduiding)
        self.fields['vertrouwelijkheidaanduiding'].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        self.fields['indicatie_intern_of_extern'].help_text += f"\n\n{value_display_mapping}"
