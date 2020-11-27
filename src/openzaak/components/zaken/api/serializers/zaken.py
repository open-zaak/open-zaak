# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_gis.fields import GeometryField
from rest_framework_nested.relations import NestedHyperlinkedRelatedField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from vng_api_common.constants import (
    Archiefnominatie,
    Archiefstatus,
    RelatieAarden,
    RolOmschrijving,
    RolTypes,
)
from vng_api_common.polymorphism import Discriminator, PolymorphicSerializer
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)
from vng_api_common.utils import get_help_text
from vng_api_common.validators import (
    IsImmutableValidator,
    ResourceValidator,
    UntilNowValidator,
)

from openzaak.components.documenten.api.fields import EnkelvoudigInformatieObjectField
from openzaak.utils.api import create_remote_oio
from openzaak.utils.auth import get_auth
from openzaak.utils.exceptions import DetermineProcessEndDateException
from openzaak.utils.validators import (
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
    ObjecttypeInformatieobjecttypeRelationValidator,
    PublishValidator,
)

from ...brondatum import BrondatumCalculator
from ...constants import AardZaakRelatie, BetalingsIndicatie, IndicatieMachtiging
from ...models import (
    KlantContact,
    RelevanteZaakRelatie,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakBesluit,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakKenmerk,
)
from ..validators import (
    CorrectZaaktypeValidator,
    DateNotInFutureValidator,
    EndStatusIOsIndicatieGebruiksrechtValidator,
    EndStatusIOsUnlockedValidator,
    HoofdzaakValidator,
    NotSelfValidator,
    RolOccurenceValidator,
    UniekeIdentificatieValidator,
    ZaakArchiveIOsArchivedValidator,
)
from .betrokkenen import (
    RolMedewerkerSerializer,
    RolNatuurlijkPersoonSerializer,
    RolNietNatuurlijkPersoonSerializer,
    RolOrganisatorischeEenheidSerializer,
    RolVestigingSerializer,
)

logger = logging.getLogger(__name__)


# Zaak API
class ZaakKenmerkSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ZaakKenmerk
        fields = ("kenmerk", "bron")


class VerlengingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Zaak
        gegevensgroep = "verlenging"
        extra_kwargs = {"reden": {"label": _("Reden")}, "duur": {"label": _("Duur")}}


class OpschortingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Zaak
        gegevensgroep = "opschorting"
        extra_kwargs = {
            "indicatie": {"label": _("Indicatie")},
            "reden": {"label": _("Reden"), "allow_blank": True},
        }


class RelevanteZaakSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RelevanteZaakRelatie
        fields = ("url", "aard_relatie")
        extra_kwargs = {
            "url": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [LooseFkResourceValidator("Zaak", settings.ZRC_API_SPEC)],
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(AardZaakRelatie)
        self.fields["aard_relatie"].help_text += f"\n\n{value_display_mapping}"


class ZaakSerializer(
    NestedGegevensGroepMixin,
    NestedCreateMixin,
    NestedUpdateMixin,
    serializers.HyperlinkedModelSerializer,
):
    eigenschappen = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        lookup_field="uuid",
        view_name="zaakeigenschap-detail",
        parent_lookup_kwargs={"zaak_uuid": "zaak__uuid"},
        source="zaakeigenschap_set",
    )
    status = serializers.HyperlinkedRelatedField(
        source="current_status_uuid",
        read_only=True,
        allow_null=True,
        view_name="status-detail",
        lookup_url_kwarg="uuid",
        help_text=_("Indien geen status bekend is, dan is de waarde 'null'"),
    )

    kenmerken = ZaakKenmerkSerializer(
        source="zaakkenmerk_set",
        many=True,
        required=False,
        help_text="Lijst van kenmerken. Merk op dat refereren naar gerelateerde objecten "
        "beter kan via `ZaakObject`.",
    )

    betalingsindicatie_weergave = serializers.CharField(
        source="get_betalingsindicatie_display",
        read_only=True,
        help_text=_("Uitleg bij `betalingsindicatie`."),
    )

    verlenging = VerlengingSerializer(
        required=False,
        allow_null=True,
        help_text=_(
            "Gegevens omtrent het verlengen van de doorlooptijd van de behandeling van de ZAAK"
        ),
    )

    opschorting = OpschortingSerializer(
        required=False,
        allow_null=True,
        help_text=_(
            "Gegevens omtrent het tijdelijk opschorten van de behandeling van de ZAAK"
        ),
    )

    deelzaken = serializers.HyperlinkedRelatedField(
        read_only=True,
        many=True,
        view_name="zaak-detail",
        lookup_url_kwarg="uuid",
        lookup_field="uuid",
        help_text=_("URL-referenties naar deel ZAAKen."),
    )

    resultaat = serializers.HyperlinkedRelatedField(
        read_only=True,
        allow_null=True,
        view_name="resultaat-detail",
        lookup_url_kwarg="uuid",
        lookup_field="uuid",
        help_text=_(
            "URL-referentie naar het RESULTAAT. Indien geen resultaat bekend is, dan is de waarde 'null'"
        ),
    )

    relevante_andere_zaken = RelevanteZaakSerializer(
        many=True, required=False, help_text=_("Een lijst van relevante andere zaken.")
    )

    class Meta:
        model = Zaak
        fields = (
            "url",
            "uuid",
            "identificatie",
            "bronorganisatie",
            "omschrijving",
            "toelichting",
            "zaaktype",
            "registratiedatum",
            "verantwoordelijke_organisatie",
            "startdatum",
            "einddatum",
            "einddatum_gepland",
            "uiterlijke_einddatum_afdoening",
            "publicatiedatum",
            "communicatiekanaal",
            # TODO: add shape validator once we know the shape
            "producten_of_diensten",
            "vertrouwelijkheidaanduiding",
            "betalingsindicatie",
            "betalingsindicatie_weergave",
            "laatste_betaaldatum",
            "zaakgeometrie",
            "verlenging",
            "opschorting",
            "selectielijstklasse",
            "hoofdzaak",
            "deelzaken",
            "relevante_andere_zaken",
            "eigenschappen",
            # read-only veld, on-the-fly opgevraagd
            "status",
            # Writable inline resource, as opposed to eigenschappen for demo
            # purposes. Eventually, we need to choose one form.
            "kenmerken",
            # Archiving
            "archiefnominatie",
            "archiefstatus",
            "archiefactiedatum",
            "resultaat",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaaktype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("ZaakType", settings.ZTC_API_SPEC),
                    LooseFkIsImmutableValidator(),
                    PublishValidator(),
                ],
            },
            "zaakgeometrie": {
                "help_text": "Punt, lijn of (multi-)vlak geometrie-informatie, in GeoJSON."
            },
            "identificatie": {"validators": [IsImmutableValidator()]},
            "einddatum": {"read_only": True, "allow_null": True},
            "communicatiekanaal": {
                "validators": [
                    ResourceValidator(
                        "CommunicatieKanaal", settings.REFERENTIELIJSTEN_API_SPEC
                    )
                ]
            },
            "vertrouwelijkheidaanduiding": {
                "required": False,
                "help_text": _(
                    "Aanduiding van de mate waarin het zaakdossier van de "
                    "ZAAK voor de openbaarheid bestemd is. Optioneel - indien "
                    "geen waarde gekozen wordt, dan wordt de waarde van het "
                    "ZAAKTYPE overgenomen. Dit betekent dat de API _altijd_ een "
                    "waarde teruggeeft."
                ),
            },
            "selectielijstklasse": {
                "validators": [
                    ResourceValidator(
                        "Resultaat",
                        settings.REFERENTIELIJSTEN_API_SPEC,
                        get_auth=get_auth,
                    )
                ]
            },
            "hoofdzaak": {
                "lookup_field": "uuid",
                "queryset": Zaak.objects.all(),
                "validators": [NotSelfValidator(), HoofdzaakValidator()],
            },
            "laatste_betaaldatum": {"validators": [UntilNowValidator()]},
        }
        # Replace a default "unique together" constraint.
        validators = [
            UniekeIdentificatieValidator(),
            ZaakArchiveIOsArchivedValidator(),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(BetalingsIndicatie)
        self.fields["betalingsindicatie"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefstatus)
        self.fields["archiefstatus"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        self.fields["archiefnominatie"].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        super().validate(attrs)

        default_betalingsindicatie = (
            self.instance.betalingsindicatie if self.instance else None
        )
        betalingsindicatie = attrs.get("betalingsindicatie", default_betalingsindicatie)
        if betalingsindicatie == BetalingsIndicatie.nvt and attrs.get(
            "laatste_betaaldatum"
        ):
            raise serializers.ValidationError(
                {
                    "laatste_betaaldatum": _(
                        'Laatste betaaldatum kan niet gezet worden als de betalingsindicatie "nvt" is'
                    )
                },
                code="betaling-nvt",
            )

        # check that productenOfDiensten are part of the ones on the zaaktype
        default_zaaktype = self.instance.zaaktype if self.instance else None
        zaaktype = attrs.get("zaaktype", default_zaaktype)
        assert zaaktype, "Should not have passed validation - a zaaktype is needed"

        producten_of_diensten = attrs.get("producten_of_diensten")
        if producten_of_diensten:
            if not set(producten_of_diensten).issubset(
                set(zaaktype.producten_of_diensten)
            ):
                raise serializers.ValidationError(
                    {
                        "producten_of_diensten": _(
                            "Niet alle producten/diensten komen voor in "
                            "de producten/diensten op het zaaktype"
                        )
                    },
                    code="invalid-products-services",
                )

        return attrs

    def create(self, validated_data: dict):
        # set the derived value from ZTC
        if "vertrouwelijkheidaanduiding" not in validated_data:
            zaaktype = validated_data["zaaktype"]
            validated_data[
                "vertrouwelijkheidaanduiding"
            ] = zaaktype.vertrouwelijkheidaanduiding

        return super().create(validated_data)


class GeoWithinSerializer(serializers.Serializer):
    within = GeometryField(required=False)


class ZaakZoekSerializer(serializers.Serializer):
    zaakgeometrie = GeoWithinSerializer(required=True)


class StatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = (
            "url",
            "uuid",
            "zaak",
            "statustype",
            "datum_status_gezet",
            "statustoelichting",
        )
        validators = [
            CorrectZaaktypeValidator("statustype"),
            EndStatusIOsUnlockedValidator(),
            EndStatusIOsIndicatieGebruiksrechtValidator(),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "datum_status_gezet": {"validators": [DateNotInFutureValidator()]},
            "statustype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("StatusType", settings.ZTC_API_SPEC),
                ],
            },
        }

    def to_internal_value(self, data: dict) -> dict:
        """
        Convert the data to native Python objects.

        This runs before self.validate(...) is called.
        """
        attrs = super().to_internal_value(data)

        statustype = attrs["statustype"]

        if isinstance(statustype, ProxyMixin):
            attrs["__is_eindstatus"] = statustype._initial_data["is_eindstatus"]
        else:
            attrs["__is_eindstatus"] = statustype.is_eindstatus()
        return attrs

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        # validate that all InformationObjects have indicatieGebruiksrecht set
        # and are unlocked
        if validated_attrs["__is_eindstatus"]:
            zaak = validated_attrs["zaak"]

            brondatum_calculator = BrondatumCalculator(
                zaak, validated_attrs["datum_status_gezet"]
            )
            try:
                brondatum_calculator.calculate()
            except Resultaat.DoesNotExist as exc:
                raise serializers.ValidationError(
                    exc.args[0], code="resultaat-does-not-exist"
                ) from exc
            except DetermineProcessEndDateException as exc:
                # ideally, we'd like to do this in the validate function, but that's unfortunately too
                # early since we don't know the end date yet
                # thought: we _can_ use the datumStatusGezet though!
                raise serializers.ValidationError(
                    exc.args[0], code="archiefactiedatum-error"
                )

            # nasty to pass state around...
            self.context["brondatum_calculator"] = brondatum_calculator

        return validated_attrs

    def create(self, validated_data):
        """
        Perform additional business logic

        Ideally, this would be encapsulated in some utilities for a clear in-output
        system, but for now we need to put a bandage on it.

        NOTE: avoid doing queries outside of the transaction block - we want
        everything or nothing to succeed and no limbo states.
        """
        zaak = validated_data["zaak"]
        _zaak_fields_changed = []

        is_eindstatus = validated_data.pop("__is_eindstatus")
        brondatum_calculator = self.context.pop("brondatum_calculator", None)

        # are we re-opening the case?
        is_reopening = zaak.einddatum and not is_eindstatus

        # if the eindstatus is being set, we need to calculate some more things:
        # 1. zaak.einddatum, which may be relevant for archiving purposes
        # 2. zaak.archiefactiedatum, if not explicitly filled in
        if is_eindstatus:
            zaak.einddatum = validated_data["datum_status_gezet"].date()
        else:
            zaak.einddatum = None
        _zaak_fields_changed.append("einddatum")

        if is_eindstatus:
            # in case of eindstatus - retrieve archive parameters from resultaattype

            # Archiving: Use default archiefnominatie
            if not zaak.archiefnominatie:
                zaak.archiefnominatie = brondatum_calculator.get_archiefnominatie()
                _zaak_fields_changed.append("archiefnominatie")

            # Archiving: Calculate archiefactiedatum
            if not zaak.archiefactiedatum:
                zaak.archiefactiedatum = brondatum_calculator.calculate()
                if zaak.archiefactiedatum is not None:
                    _zaak_fields_changed.append("archiefactiedatum")
        elif is_reopening:
            zaak.archiefnominatie = None
            zaak.archiefactiedatum = None
            _zaak_fields_changed += ["archiefnominatie", "archiefactiedatum"]

        with transaction.atomic():
            obj = super().create(validated_data)

            # Save updated information on the ZAAK
            zaak.save(update_fields=_zaak_fields_changed)

        return obj


class ZaakInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    aard_relatie_weergave = serializers.ChoiceField(
        source="get_aard_relatie_display",
        read_only=True,
        choices=[(force_text(value), key) for key, value in RelatieAarden.choices],
    )
    informatieobject = EnkelvoudigInformatieObjectField(
        validators=[
            LooseFkIsImmutableValidator(instance_path="canonical"),
            LooseFkResourceValidator(
                "EnkelvoudigInformatieObject", settings.DRC_API_SPEC
            ),
        ],
        max_length=1000,
        min_length=1,
        help_text=get_help_text("zaken.ZaakInformatieObject", "informatieobject"),
    )

    class Meta:
        model = ZaakInformatieObject
        fields = (
            "url",
            "uuid",
            "informatieobject",
            "zaak",
            "aard_relatie_weergave",
            "titel",
            "beschrijving",
            "registratiedatum",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=ZaakInformatieObject.objects.all(),
                fields=["zaak", "informatieobject"],
            ),
            ObjecttypeInformatieobjecttypeRelationValidator(),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid", "validators": [IsImmutableValidator()]},
        }

    def create(self, validated_data):
        with transaction.atomic():
            zio = super().create(validated_data)

        # local FK or CMIS - nothing to do -> our signals create the OIO
        if zio.informatieobject.pk or settings.CMIS_ENABLED:
            return zio

        # we know that we got valid URLs in the initial data
        io_url = self.initial_data["informatieobject"]
        zaak_url = self.initial_data["zaak"]

        # manual transaction management - documents API checks that the ZIO
        # exists, so that transaction must be committed.
        # If it fails in any other way, we need to handle that by rolling back
        # the ZIO creation.
        try:
            response = create_remote_oio(io_url, zaak_url)
        except Exception as exception:
            zio.delete()
            raise serializers.ValidationError(
                {
                    "informatieobject": _(
                        "Could not create remote relation: {exception}"
                    ).format(exception)
                },
                code="pending-relations",
            )
        else:
            zio._objectinformatieobject_url = response["url"]
            zio.save()

        return zio

    def run_validators(self, value):
        """
        Add read_only fields with defaults to value before running validators.
        """
        # In the case CMIS is enabled, we need to filter on the URL and not the canonical object
        if value.get("informatieobject") is not None and settings.CMIS_ENABLED:
            value["informatieobject"] = self.initial_data.get("informatieobject")

        return super().run_validators(value)


class ZaakEigenschapSerializer(NestedHyperlinkedModelSerializer):
    parent_lookup_kwargs = {"zaak_uuid": "zaak__uuid"}

    class Meta:
        model = ZaakEigenschap
        fields = ("url", "uuid", "zaak", "eigenschap", "naam", "waarde")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "naam": {"source": "_naam", "read_only": True},
            "eigenschap": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("Eigenschap", settings.ZTC_API_SPEC),
                ],
            },
        }
        validators = [CorrectZaaktypeValidator("eigenschap")]

    def validate(self, attrs):
        super().validate(attrs)

        eigenschap = attrs["eigenschap"]
        attrs["_naam"] = eigenschap.eigenschapnaam

        return attrs


class KlantContactSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = KlantContact
        fields = (
            "url",
            "uuid",
            "zaak",
            "identificatie",
            "datumtijd",
            "kanaal",
            "onderwerp",
            "toelichting",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "identificatie": {"required": False},
            "zaak": {"lookup_field": "uuid"},
            "datumtijd": {"validators": [DateNotInFutureValidator()]},
        }


class RolSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field="betrokkene_type",
        mapping={
            RolTypes.natuurlijk_persoon: RolNatuurlijkPersoonSerializer(),
            RolTypes.niet_natuurlijk_persoon: RolNietNatuurlijkPersoonSerializer(),
            RolTypes.vestiging: RolVestigingSerializer(),
            RolTypes.organisatorische_eenheid: RolOrganisatorischeEenheidSerializer(),
            RolTypes.medewerker: RolMedewerkerSerializer(),
        },
        group_field="betrokkene_identificatie",
        same_model=False,
    )

    class Meta:
        model = Rol
        fields = (
            "url",
            "uuid",
            "zaak",
            "betrokkene",
            "betrokkene_type",
            "roltype",
            "omschrijving",
            "omschrijving_generiek",
            "roltoelichting",
            "registratiedatum",
            "indicatie_machtiging",
        )
        validators = [
            RolOccurenceValidator(RolOmschrijving.initiator, max_amount=1),
            RolOccurenceValidator(RolOmschrijving.zaakcoordinator, max_amount=1),
            CorrectZaaktypeValidator("roltype"),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "betrokkene": {"required": False},
            "roltype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("RolType", settings.ZTC_API_SPEC),
                    LooseFkIsImmutableValidator(),
                ],
                "help_text": get_help_text("zaken.Rol", "roltype"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(IndicatieMachtiging)
        self.fields["indicatie_machtiging"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolTypes)
        self.fields["betrokkene_type"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolOmschrijving)
        self.fields["omschrijving_generiek"].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        betrokkene = validated_attrs.get("betrokkene", None)
        betrokkene_identificatie = validated_attrs.get("betrokkene_identificatie", None)

        if not betrokkene and not betrokkene_identificatie:
            raise serializers.ValidationError(
                _("betrokkene or betrokkeneIdentificatie must be provided"),
                code="invalid-betrokkene",
            )

        return validated_attrs

    @transaction.atomic
    def create(self, validated_data):
        group_data = validated_data.pop("betrokkene_identificatie", None)
        rol = super().create(validated_data)

        if group_data:
            group_serializer = self.discriminator.mapping[
                validated_data["betrokkene_type"]
            ]
            serializer = group_serializer.get_fields()["betrokkene_identificatie"]
            group_data["rol"] = rol
            serializer.create(group_data)

        return rol


class ResultaatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Resultaat
        fields = ("url", "uuid", "zaak", "resultaattype", "toelichting")
        validators = [CorrectZaaktypeValidator("resultaattype")]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "resultaattype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("ResultaatType", settings.ZTC_API_SPEC),
                    LooseFkIsImmutableValidator(),
                ],
            },
        }


class ZaakBesluitSerializer(NestedHyperlinkedModelSerializer):
    """
    Serializer the reverse relation between Besluit-Zaak.
    """

    parent_lookup_kwargs = {"zaak_uuid": "zaak__uuid"}

    class Meta:
        model = ZaakBesluit
        fields = ("url", "uuid", "besluit")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "besluit": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("Besluit", settings.BRC_API_SPEC),
                ],
            },
        }

    def create(self, validated_data):
        validated_data["zaak"] = self.context["parent_object"]
        return super().create(validated_data)
