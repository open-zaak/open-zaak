import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Max, Subquery
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from openzaak.components.besluiten.models import Besluit
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectHyperlinkedRelatedField
)
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical
)
from openzaak.components.zaken.models import (
    KlantContact, RelevanteZaakRelatie, Resultaat, Rol, Status, Zaak,
    ZaakBesluit, ZaakEigenschap, ZaakInformatieObject, ZaakKenmerk, ZaakObject
)
from openzaak.components.zaken.models.constants import (
    AardZaakRelatie, BetalingsIndicatie, IndicatieMachtiging
)
from openzaak.components.zaken.models.utils import BrondatumCalculator
from openzaak.utils.auth import get_auth
from openzaak.utils.exceptions import DetermineProcessEndDateException
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_gis.fields import GeometryField
from rest_framework_nested.relations import NestedHyperlinkedIdentityField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from vng_api_common.constants import (
    Archiefnominatie, Archiefstatus, RelatieAarden, RolOmschrijving, RolTypes,
    ZaakobjectTypes
)
from vng_api_common.polymorphism import Discriminator, PolymorphicSerializer
from vng_api_common.serializers import (
    GegevensGroepSerializer, NestedGegevensGroepMixin,
    add_choice_values_help_text
)
from vng_api_common.utils import get_help_text
from vng_api_common.validators import (
    IsImmutableValidator, ResourceValidator, UntilNowValidator, URLValidator
)

from ..validators import (
    CorrectZaaktypeValidator, DateNotInFutureValidator, HoofdzaakValidator,
    NotSelfValidator, RolOccurenceValidator, UniekeIdentificatieValidator,
    ZaaktypeInformatieobjecttypeRelationValidator
)
from .address import ObjectAdresSerializer
from .betrokkene import (
    RolMedewerkerSerializer, RolNatuurlijkPersoonSerializer,
    RolNietNatuurlijkPersoonSerializer, RolOrganisatorischeEenheidSerializer,
    RolVestigingSerializer
)
from .zaakobjecten import (
    ObjectBuurtSerializer, ObjectGemeentelijkeOpenbareRuimteSerializer,
    ObjectGemeenteSerializer, ObjectHuishoudenSerializer,
    ObjectInrichtingselementSerializer,
    ObjectKadastraleOnroerendeZaakSerializer, ObjectKunstwerkdeelSerializer,
    ObjectMaatschappelijkeActiviteitSerializer, ObjectOpenbareRuimteSerializer,
    ObjectOverigeSerializer, ObjectPandSerializer,
    ObjectSpoorbaandeelSerializer, ObjectTerreindeelSerializer,
    ObjectTerreinGebouwdObjectSerializer, ObjectWaterdeelSerializer,
    ObjectWegdeelSerializer, ObjectWijkSerializer, ObjectWoonplaatsSerializer,
    ObjectWozDeelobjectSerializer, ObjectWozObjectSerializer,
    ObjectWozWaardeSerializer, ObjectZakelijkRechtSerializer
)

logger = logging.getLogger(__name__)


# Zaak API
class ZaakKenmerkSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ZaakKenmerk
        fields = (
            'kenmerk',
            'bron',
        )


class VerlengingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Zaak
        gegevensgroep = 'verlenging'
        extra_kwargs = {
            'reden': {
                'label': _("Reden"),
            },
            'duur': {
                'label': _("Duur"),
            }
        }


class OpschortingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Zaak
        gegevensgroep = 'opschorting'
        extra_kwargs = {
            'indicatie': {
                'label': _("Indicatie"),
            },
            'reden': {
                'label': _("Reden"),
                'allow_blank': True,
            }
        }


class RelevanteZaakSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelevanteZaakRelatie
        fields = ('url', 'aard_relatie',)
        extra_kwargs = {
            'url': {
                'validators': [
                    ResourceValidator('Zaak', settings.ZRC_API_SPEC, get_auth=get_auth,
                                      headers={'Accept-Crs': 'EPSG:4326'})
                ]
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(AardZaakRelatie)
        self.fields['aard_relatie'].help_text += f"\n\n{value_display_mapping}"


class ZaakSerializer(NestedGegevensGroepMixin, NestedCreateMixin, NestedUpdateMixin,
                     serializers.HyperlinkedModelSerializer):
    status = serializers.HyperlinkedRelatedField(
        source='current_status_uuid',
        read_only=True,
        allow_null=True,
        view_name='status-detail',
        lookup_url_kwarg='uuid',
        help_text=_("Indien geen status bekend is, dan is de waarde 'null'")
    )

    kenmerken = ZaakKenmerkSerializer(
        source='zaakkenmerk_set',
        many=True,
        required=False,
        help_text="Lijst van kenmerken. Merk op dat refereren naar gerelateerde objecten "
                  "beter kan via `ZaakObject`."
    )

    betalingsindicatie_weergave = serializers.CharField(
        source='get_betalingsindicatie_display', read_only=True,
        help_text=_('Uitleg bij `betalingsindicatie`.')
    )

    verlenging = VerlengingSerializer(
        required=False, allow_null=True,
        help_text=_("Gegevens omtrent het verlengen van de doorlooptijd van de behandeling van de ZAAK")
    )

    opschorting = OpschortingSerializer(
        required=False, allow_null=True,
        help_text=_("Gegevens omtrent het tijdelijk opschorten van de behandeling van de ZAAK")
    )

    deelzaken = serializers.HyperlinkedRelatedField(
        read_only=True,
        many=True,
        view_name='zaak-detail',
        lookup_url_kwarg='uuid',
        lookup_field='uuid',
        help_text=_('URL-referenties naar deel ZAAKen.')
    )

    resultaat = serializers.HyperlinkedRelatedField(
        read_only=True,
        allow_null=True,
        view_name='resultaat-detail',
        lookup_url_kwarg='uuid',
        lookup_field='uuid',
        help_text=_("URL-referentie naar het RESULTAAT. Indien geen resultaat bekend is, dan is de waarde 'null'")
    )

    relevante_andere_zaken = RelevanteZaakSerializer(
        many=True, required=False,
        help_text=_(
            "Een lijst van relevante andere zaken."
        )
    )

    class Meta:
        model = Zaak
        fields = (
            'url',
            'uuid',
            'identificatie',
            'bronorganisatie',
            'omschrijving',
            'toelichting',
            'zaaktype',
            'registratiedatum',
            'verantwoordelijke_organisatie',
            'startdatum',
            'einddatum',
            'einddatum_gepland',
            'uiterlijke_einddatum_afdoening',
            'publicatiedatum',
            'communicatiekanaal',
            # TODO: add shape validator once we know the shape
            'producten_of_diensten',
            'vertrouwelijkheidaanduiding',
            'betalingsindicatie',
            'betalingsindicatie_weergave',
            'laatste_betaaldatum',
            'zaakgeometrie',
            'verlenging',
            'opschorting',
            'selectielijstklasse',
            'hoofdzaak',
            'deelzaken',
            'relevante_andere_zaken',

            # read-only veld, on-the-fly opgevraagd
            'status',

            # Writable inline resource, as opposed to eigenschappen for demo
            # purposes. Eventually, we need to choose one form.
            'kenmerken',

            # Archiving
            'archiefnominatie',
            'archiefstatus',
            'archiefactiedatum',

            'resultaat',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaakgeometrie': {
                'help_text': 'Punt, lijn of (multi-)vlak geometrie-informatie, in GeoJSON.'
            },
            'identificatie': {
                'validators': [IsImmutableValidator()],
            },
            'zaaktype': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()],
            },
            'einddatum': {
                'read_only': True,
                'allow_null': True,
            },
            'communicatiekanaal': {
                'validators': [
                    ResourceValidator('CommunicatieKanaal', settings.REFERENTIELIJSTEN_API_SPEC)
                ]
            },
            'vertrouwelijkheidaanduiding': {
                'required': False,
                'help_text': _("Aanduiding van de mate waarin het zaakdossier van de "
                               "ZAAK voor de openbaarheid bestemd is. Optioneel - indien "
                               "geen waarde gekozen wordt, dan wordt de waarde van het "
                               "ZAAKTYPE overgenomen. Dit betekent dat de API _altijd_ een "
                               "waarde teruggeeft.")
            },
            'selectielijstklasse': {
                'validators': [
                    ResourceValidator('Resultaat', settings.REFERENTIELIJSTEN_API_SPEC, get_auth=get_auth)
                ]
            },
            'hoofdzaak': {
                'lookup_field': 'uuid',
                'queryset': Zaak.objects.all(),
                'validators': [NotSelfValidator(), HoofdzaakValidator()],
            },
            'laatste_betaaldatum': {
                'validators': [UntilNowValidator()]
            }
        }
        # Replace a default "unique together" constraint.
        validators = [UniekeIdentificatieValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(BetalingsIndicatie)
        self.fields['betalingsindicatie'].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefstatus)
        self.fields['archiefstatus'].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        self.fields['archiefnominatie'].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        super().validate(attrs)

        default_betalingsindicatie = self.instance.betalingsindicatie if self.instance else None
        betalingsindicatie = attrs.get('betalingsindicatie', default_betalingsindicatie)
        if betalingsindicatie == BetalingsIndicatie.nvt and attrs.get('laatste_betaaldatum'):
            raise serializers.ValidationError({'laatste_betaaldatum': _(
                "Laatste betaaldatum kan niet gezet worden als de betalingsindicatie \"nvt\" is"
            )}, code='betaling-nvt')

        # check that productenOfDiensten are part of the ones on the zaaktype
        default_zaaktype = self.instance.zaaktype if self.instance else None
        zaaktype = attrs.get('zaaktype', default_zaaktype)
        assert zaaktype, "Should not have passed validation - a zaaktype is needed"

        producten_of_diensten = attrs.get('producten_of_diensten')
        if producten_of_diensten:
            if not set(producten_of_diensten).issubset(set(zaaktype.producten_of_diensten)):
                raise serializers.ValidationError({
                    'producten_of_diensten': _("Niet alle producten/diensten komen voor in "
                                               "de producten/diensten op het zaaktype")
                }, code='invalid-products-services')

        # Archiving
        default_archiefstatus = self.instance.archiefstatus if self.instance else Archiefstatus.nog_te_archiveren
        archiefstatus = attrs.get('archiefstatus', default_archiefstatus) != Archiefstatus.nog_te_archiveren
        if archiefstatus:
            # search for related informatieobjects with status != 'gearchiveerd'
            canonical_ids = self.instance.zaakinformatieobject_set.values('informatieobject_id')
            io_ids = EnkelvoudigInformatieObjectCanonical.objects.filter(id__in=Subquery(canonical_ids))\
                .annotate(last=Max('enkelvoudiginformatieobject')).values('last')

            if EnkelvoudigInformatieObject.objects\
                    .filter(id__in=Subquery(io_ids))\
                    .exclude(status='gearchiveerd').exists():

                raise serializers.ValidationError({
                    'archiefstatus',
                    _("Er zijn gerelateerde informatieobjecten waarvan de `status` nog niet gelijk is aan "
                      "`gearchiveerd`. Dit is een voorwaarde voor het zetten van de `archiefstatus` op een andere "
                      "waarde dan `nog_te_archiveren`.")
                }, code='documents-not-archived')

            for attr in ['archiefnominatie', 'archiefactiedatum']:
                if not attrs.get(attr, getattr(self.instance, attr) if self.instance else None):
                    raise serializers.ValidationError({
                        attr: _("Moet van een waarde voorzien zijn als de 'Archiefstatus' een waarde heeft anders dan "
                                "'nog_te_archiveren'.")
                    }, code=f'{attr}-not-set')
        # End archiving

        return attrs

    def create(self, validated_data: dict):
        # set the derived value from ZTC
        if 'vertrouwelijkheidaanduiding' not in validated_data:
            zaaktype = validated_data['zaaktype']
            validated_data['vertrouwelijkheidaanduiding'] = zaaktype.vertrouwelijkheidaanduiding

        return super().create(validated_data)


class GeoWithinSerializer(serializers.Serializer):
    within = GeometryField(required=False)


class ZaakZoekSerializer(serializers.Serializer):
    zaakgeometrie = GeoWithinSerializer(required=True)


class StatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = (
            'url',
            'uuid',
            'zaak',
            'statustype',
            'datum_status_gezet',
            'statustoelichting'
        )
        validators = [
            CorrectZaaktypeValidator('statustype')
        ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'statustype': {
                'lookup_field': 'uuid',
            },
            'datum_status_gezet': {
                'validators': [
                    DateNotInFutureValidator()
                ]
            }
        }

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        statustype = validated_attrs['statustype']
        validated_attrs['__is_eindstatus'] = statustype.is_eindstatus()

        # validate that all InformationObjects have indicatieGebruiksrecht set
        # and are unlocked
        if validated_attrs['__is_eindstatus']:
            zaak = validated_attrs['zaak']

            if zaak.zaakinformatieobject_set.exclude(informatieobject__lock='').exists():
                raise serializers.ValidationError(
                    "Er zijn gerelateerde informatieobjecten die nog gelocked zijn."
                    "Deze informatieobjecten moet eerst unlocked worden voordat de zaak afgesloten kan worden.",
                    code='informatieobject-locked'
                )
            canonical_ids = zaak.zaakinformatieobject_set.values('informatieobject_id')
            io_ids = EnkelvoudigInformatieObjectCanonical.objects.filter(id__in=Subquery(canonical_ids))\
                .annotate(last=Max('enkelvoudiginformatieobject')).values('last')

            if EnkelvoudigInformatieObject.objects\
                    .filter(id__in=Subquery(io_ids))\
                    .filter(indicatie_gebruiksrecht__isnull=True).exists():

                    # zios = zaak.zaakinformatieobject_set.all()
                    # for zio in zios:
                    #     informatieobject = zio.informatieobject
                    #     if informatieobject.latest_version.indicatie_gebruiksrecht is None:
                raise serializers.ValidationError(
                    "Er zijn gerelateerde informatieobjecten waarvoor `indicatieGebruiksrecht` nog niet "
                    "gespecifieerd is. Je moet deze zetten voor je de zaak kan afsluiten.",
                    code='indicatiegebruiksrecht-unset'
                )

            brondatum_calculator = BrondatumCalculator(zaak, validated_attrs['datum_status_gezet'])
            try:
                brondatum_calculator.calculate()
            except Resultaat.DoesNotExist as exc:
                raise serializers.ValidationError(
                    exc.args[0],
                    code='resultaat-does-not-exist'
                ) from exc
            except DetermineProcessEndDateException as exc:
                # ideally, we'd like to do this in the validate function, but that's unfortunately too
                # early since we don't know the end date yet
                # thought: we _can_ use the datumStatusGezet though!
                raise serializers.ValidationError(exc.args[0], code='archiefactiedatum-error')

            # nasty to pass state around...
            self.context['brondatum_calculator'] = brondatum_calculator

        return validated_attrs

    def create(self, validated_data):
        """
        Perform additional business logic

        Ideally, this would be encapsulated in some utilities for a clear in-output
        system, but for now we need to put a bandage on it.

        NOTE: avoid doing queries outside of the transaction block - we want
        everything or nothing to succeed and no limbo states.
        """
        zaak = validated_data['zaak']
        _zaak_fields_changed = []

        is_eindstatus = validated_data.pop('__is_eindstatus')
        brondatum_calculator = self.context.pop('brondatum_calculator', None)

        # are we re-opening the case?
        is_reopening = zaak.einddatum and not is_eindstatus

        # if the eindstatus is being set, we need to calculate some more things:
        # 1. zaak.einddatum, which may be relevant for archiving purposes
        # 2. zaak.archiefactiedatum, if not explicitly filled in
        if is_eindstatus:
            zaak.einddatum = validated_data['datum_status_gezet'].date()
        else:
            zaak.einddatum = None
        _zaak_fields_changed.append('einddatum')

        if is_eindstatus:
            # in case of eindstatus - retrieve archive parameters from resultaattype

            # Archiving: Use default archiefnominatie
            if not zaak.archiefnominatie:
                zaak.archiefnominatie = brondatum_calculator.get_archiefnominatie()
                _zaak_fields_changed.append('archiefnominatie')

            # Archiving: Calculate archiefactiedatum
            if not zaak.archiefactiedatum:
                zaak.archiefactiedatum = brondatum_calculator.calculate()
                if zaak.archiefactiedatum is not None:
                    _zaak_fields_changed.append('archiefactiedatum')
        elif is_reopening:
            zaak.archiefnominatie = None
            zaak.archiefactiedatum = None
            _zaak_fields_changed += ['archiefnominatie', 'archiefactiedatum']

        with transaction.atomic():
            obj = super().create(validated_data)

            # Save updated information on the ZAAK
            zaak.save(update_fields=_zaak_fields_changed)

        return obj


class ZaakObjectSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field='object_type',
        mapping={
            ZaakobjectTypes.adres: ObjectAdresSerializer(),
            ZaakobjectTypes.besluit: None,
            ZaakobjectTypes.buurt: ObjectBuurtSerializer(),
            ZaakobjectTypes.enkelvoudig_document: None,
            ZaakobjectTypes.gemeente: ObjectGemeenteSerializer(),
            ZaakobjectTypes.gemeentelijke_openbare_ruimte: ObjectGemeentelijkeOpenbareRuimteSerializer(),
            ZaakobjectTypes.huishouden: ObjectHuishoudenSerializer(),
            ZaakobjectTypes.inrichtingselement: ObjectInrichtingselementSerializer(),
            ZaakobjectTypes.kadastrale_onroerende_zaak: ObjectKadastraleOnroerendeZaakSerializer(),
            ZaakobjectTypes.kunstwerkdeel: ObjectKunstwerkdeelSerializer(),
            ZaakobjectTypes.maatschappelijke_activiteit: ObjectMaatschappelijkeActiviteitSerializer(),
            ZaakobjectTypes.medewerker: RolMedewerkerSerializer(),
            ZaakobjectTypes.natuurlijk_persoon: RolNatuurlijkPersoonSerializer(),
            ZaakobjectTypes.niet_natuurlijk_persoon: RolNietNatuurlijkPersoonSerializer(),
            ZaakobjectTypes.openbare_ruimte: ObjectOpenbareRuimteSerializer(),
            ZaakobjectTypes.organisatorische_eenheid: RolOrganisatorischeEenheidSerializer(),
            ZaakobjectTypes.pand: ObjectPandSerializer(),
            ZaakobjectTypes.spoorbaandeel: ObjectSpoorbaandeelSerializer(),
            ZaakobjectTypes.status: None,
            ZaakobjectTypes.terreindeel: ObjectTerreindeelSerializer(),
            ZaakobjectTypes.terrein_gebouwd_object: ObjectTerreinGebouwdObjectSerializer(),
            ZaakobjectTypes.vestiging: RolVestigingSerializer(),
            ZaakobjectTypes.waterdeel: ObjectWaterdeelSerializer(),
            ZaakobjectTypes.wegdeel: ObjectWegdeelSerializer(),
            ZaakobjectTypes.wijk: ObjectWijkSerializer(),
            ZaakobjectTypes.woonplaats: ObjectWoonplaatsSerializer(),
            ZaakobjectTypes.woz_deelobject: ObjectWozDeelobjectSerializer(),
            ZaakobjectTypes.woz_object: ObjectWozObjectSerializer(),
            ZaakobjectTypes.woz_waarde: ObjectWozWaardeSerializer(),
            ZaakobjectTypes.zakelijk_recht: ObjectZakelijkRechtSerializer(),
            ZaakobjectTypes.overige: ObjectOverigeSerializer(),
        },
        group_field='object_identificatie',
        same_model=False
    )

    class Meta:
        model = ZaakObject
        fields = (
            'url',
            'uuid',
            'zaak',
            'object',
            'object_type',
            'object_type_overige',
            'relatieomschrijving',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'object': {
                'required': False,
                'validators': [URLValidator()]
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(ZaakobjectTypes)
        self.fields['object_type'].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        object = validated_attrs.get('object', None)
        object_identificatie = validated_attrs.get('object_identificatie', None)

        if not object and not object_identificatie:
            raise serializers.ValidationError(
                _("betrokkene or betrokkeneIdentificatie must be provided"),
                code='invalid-zaakobject')

        object_type = validated_attrs.get('object_type', None)
        object_type_overige = validated_attrs.get('object_type_overige', None)

        if object_type == ZaakobjectTypes.overige and not object_type_overige:
            raise serializers.ValidationError(
                _('Als `objectType` de waarde "overige" heeft, moet '
                  '`objectTypeOverige` van een waarde voorzien zijn.'),
                code='missing-object-type-overige')

        if object_type != ZaakobjectTypes.overige and object_type_overige:
            raise serializers.ValidationError(
                _('Als `objectType` niet de waarde "overige" heeft, mag '
                  '`objectTypeOverige` niet van een waarde voorzien zijn.'),
                code='invalid-object-type-overige-usage')

        return validated_attrs

    @transaction.atomic
    def create(self, validated_data):
        group_data = validated_data.pop('object_identificatie', None)
        zaakobject = super().create(validated_data)

        if group_data:
            group_serializer = self.discriminator.mapping[validated_data['object_type']]
            serializer = group_serializer.get_fields()['object_identificatie']
            group_data['zaakobject'] = zaakobject
            serializer.create(group_data)

        return zaakobject


class ZaakInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    aard_relatie_weergave = serializers.ChoiceField(
        source='get_aard_relatie_display', read_only=True,
        choices=[(force_text(value), key) for key, value in RelatieAarden.choices]
    )
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name='enkelvoudiginformatieobject-detail',
        lookup_field='uuid',
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text('documenten.Gebruiksrechten', 'informatieobject'),
        validators=[IsImmutableValidator()]
    )

    class Meta:
        model = ZaakInformatieObject
        fields = (
            'url',
            'uuid',
            'informatieobject',
            'zaak',
            'aard_relatie_weergave',
            'titel',
            'beschrijving',
            'registratiedatum',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=ZaakInformatieObject.objects.all(),
                fields=['zaak', 'informatieobject']
            ),
            ZaaktypeInformatieobjecttypeRelationValidator()
        ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()],
            },
        }


class ZaakEigenschapSerializer(NestedHyperlinkedModelSerializer):
    parent_lookup_kwargs = {
        'zaak_uuid': 'zaak__uuid'
    }

    class Meta:
        model = ZaakEigenschap
        fields = (
            'url',
            'uuid',
            'zaak',
            'eigenschap',
            'naam',
            'waarde',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'eigenschap': {
                'lookup_field': 'uuid',
            },
            'naam': {
                'source': '_naam',
                'read_only': True,
            }
        }

    def validate(self, attrs):
        super().validate(attrs)

        eigenschap = attrs['eigenschap']
        attrs['_naam'] = eigenschap.eigenschapnaam

        return attrs


class KlantContactSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = KlantContact
        fields = (
            'url',
            'uuid',
            'zaak',
            'identificatie',
            'datumtijd',
            'kanaal',
        )
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'identificatie': {
                'required': False
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'datumtijd': {
                'validators': [DateNotInFutureValidator()]
            }
        }


class RolSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field='betrokkene_type',
        mapping={
            RolTypes.natuurlijk_persoon: RolNatuurlijkPersoonSerializer(),
            RolTypes.niet_natuurlijk_persoon: RolNietNatuurlijkPersoonSerializer(),
            RolTypes.vestiging: RolVestigingSerializer(),
            RolTypes.organisatorische_eenheid: RolOrganisatorischeEenheidSerializer(),
            RolTypes.medewerker: RolMedewerkerSerializer()
        },
        group_field='betrokkene_identificatie',
        same_model=False
    )

    class Meta:
        model = Rol
        fields = (
            'url',
            'uuid',
            'zaak',
            'betrokkene',
            'betrokkene_type',
            'roltype',
            'omschrijving',
            'omschrijving_generiek',
            'roltoelichting',
            'registratiedatum',
            'indicatie_machtiging',
        )
        validators = [
            RolOccurenceValidator(RolOmschrijving.initiator, max_amount=1),
            RolOccurenceValidator(RolOmschrijving.zaakcoordinator, max_amount=1),
            CorrectZaaktypeValidator("roltype"),
        ]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'betrokkene': {
                'required': False,
            },
            'roltype': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()],
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(IndicatieMachtiging)
        self.fields['indicatie_machtiging'].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolTypes)
        self.fields['betrokkene_type'].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolOmschrijving)
        self.fields['omschrijving_generiek'].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        betrokkene = validated_attrs.get('betrokkene', None)
        betrokkene_identificatie = validated_attrs.get('betrokkene_identificatie', None)

        if not betrokkene and not betrokkene_identificatie:
            raise serializers.ValidationError(
                _("betrokkene or betrokkeneIdentificatie must be provided"),
                code='invalid-betrokkene')

        return validated_attrs

    @transaction.atomic
    def create(self, validated_data):
        group_data = validated_data.pop('betrokkene_identificatie', None)
        rol = super().create(validated_data)

        if group_data:
            group_serializer = self.discriminator.mapping[validated_data['betrokkene_type']]
            serializer = group_serializer.get_fields()['betrokkene_identificatie']
            group_data['rol'] = rol
            serializer.create(group_data)

        return rol


class ResultaatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Resultaat
        fields = (
            'url',
            'uuid',
            'zaak',
            'resultaattype',
            'toelichting'
        )
        validators = [CorrectZaaktypeValidator('resultaattype')]
        extra_kwargs = {
            'url': {
                'lookup_field': 'uuid',
            },
            'uuid': {
                'read_only': True,
            },
            'zaak': {
                'lookup_field': 'uuid',
            },
            'resultaattype': {
                'lookup_field': 'uuid',
                'validators': [IsImmutableValidator()],
            }
        }


class ZaakBesluitSerializer(serializers.Serializer):
    """
    Serializer the reverse relation between Besluit-Zaak.

    We use the UUID of the Besluit to generate the URL/UUID of the ZaakBesluit
    instance, since it's a FK relationship, we can safely do this. Effectively,
    we're feeding the :class:`Besluit` instance to this serializer.
    """
    url = NestedHyperlinkedIdentityField(
        view_name="zaakbesluit-detail",
        lookup_field="uuid",
        parent_lookup_kwargs={'zaak_uuid': 'zaak__uuid'},
        read_only=True,
    )
    uuid = serializers.UUIDField(
        help_text=_("Unieke resource identifier (UUID4)"),
        read_only=True,
    )
    besluit = serializers.HyperlinkedRelatedField(
        queryset=Besluit.objects.all(),
        view_name="besluit-detail",
        lookup_field="uuid",
        help_text=_("URL-referentie naar het BESLUIT (in de Besluiten API), waar "
                    "ook de relatieinformatie opgevraagd kan worden.")

    )

    def validate_besluit(self, besluit: Besluit):
        zaak = self.context["view"]._get_zaak()
        if not besluit.zaak == zaak:
            raise serializers.ValidationError(
                _("Het Besluit verwijst niet naar de juiste zaak"),
                code="invalid-zaak"
            )
        return besluit
