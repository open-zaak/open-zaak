# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import logging
from datetime import date
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from rest_framework_nested.relations import NestedHyperlinkedRelatedField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from vng_api_common.caching.etags import track_object_serializer
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
from vng_api_common.validators import IsImmutableValidator, UntilNowValidator

from openzaak.components.documenten.api.fields import EnkelvoudigInformatieObjectField
from openzaak.components.zaken.validators import CorrectZaaktypeValidator
from openzaak.contrib.verzoeken.validators import verzoek_validator
from openzaak.utils.api import (
    create_remote_objectcontactmoment,
    create_remote_objectverzoek,
    create_remote_oio,
)
from openzaak.utils.auth import get_auth
from openzaak.utils.exceptions import DetermineProcessEndDateException
from openzaak.utils.help_text import mark_experimental
from openzaak.utils.serializer_fields import FKOrServiceUrlField
from openzaak.utils.validators import (
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
    ObjecttypeInformatieobjecttypeRelationValidator,
    PublishValidator,
    ResourceValidator,
    UniqueTogetherValidator,
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
    ZaakContactMoment,
    ZaakEigenschap,
    ZaakIdentificatie,
    ZaakInformatieObject,
    ZaakKenmerk,
    ZaakVerzoek,
)
from ..validators import (
    DateNotInFutureValidator,
    EndStatusIOsIndicatieGebruiksrechtValidator,
    EndStatusIOsUnlockedValidator,
    HoofdZaaktypeRelationValidator,
    HoofdzaakValidator,
    NotSelfValidator,
    OverigeRelevanteZaakRelatieValidator,
    RolIndicatieMachtigingValidator,
    RolOccurenceValidator,
    StatusRolValidator,
    UniekeIdentificatieValidator,
    ZaakArchiefStatusValidator,
    ZaakArchiveIOsArchivedValidator,
    ZaakEigenschapValueValidator,
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

    def to_representation(self, instance) -> Optional[dict]:
        # if no duration is set -> the entire group is empty
        if not instance["duur"]:
            return None
        return super().to_representation(instance)


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
        fields = ("url", "aard_relatie", "overige_relatie", "toelichting")
        extra_kwargs = {
            "url": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("Zaak", settings.ZRC_API_STANDARD)
                ],
            },
        }
        validators = [OverigeRelevanteZaakRelatieValidator()]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(AardZaakRelatie)
        fields["aard_relatie"].help_text += f"\n\n{value_display_mapping}"

        return fields


class GenerateZaakIdentificatieSerializer(serializers.ModelSerializer):
    startdatum = serializers.DateField()

    class Meta:
        model = ZaakIdentificatie
        fields = ("bronorganisatie", "startdatum")

    def create(self, validated_data):
        func = import_string(
            settings.ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS.get(
                settings.ZAAK_IDENTIFICATIE_GENERATOR,
                settings.ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS.get(
                    "use-start-datum-year"
                ),
            )
        )
        return func(validated_data)

    def update(self, instance, data):  # pragma:nocover
        raise NotImplementedError("Updating is not supported in this serializer")


class ReserveZaakIdentificatieSerializer(serializers.ModelSerializer):

    class Meta:
        model = ZaakIdentificatie
        fields = (
            "zaaknummer",
            "bronorganisatie",
        )

        extra_kwargs = {
            "zaaknummer": {
                "source": "identificatie",
                "read_only": True,
            },
            "bronorganisatie": {
                "write_only": True,
            },
        }

    def create(self, validated_data):

        return self.Meta.model.objects.generate(
            validated_data["bronorganisatie"],
            date.today(),
        )

    def update(self, instance, data):  # pragma:nocover
        raise NotImplementedError("Updating is not supported in this serializer")


class ProcessobjectSerializer(GegevensGroepSerializer):
    class Meta:
        model = Zaak
        gegevensgroep = "processobject"


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
        help_text=_("URL-referenties naar ZAAK-EIGENSCHAPPen."),
    )
    rollen = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        lookup_field="uuid",
        view_name="rol-detail",
        source="rol_set",
        help_text=_("URL-referenties naar ROLLen."),
    )
    status = serializers.HyperlinkedRelatedField(
        source="current_status",
        read_only=True,
        allow_null=True,
        view_name="status-detail",
        lookup_field="uuid",
        help_text=_("Indien geen status bekend is, dan is de waarde 'null'"),
    )
    zaakinformatieobjecten = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        lookup_field="uuid",
        view_name="zaakinformatieobject-detail",
        source="zaakinformatieobject_set",
        help_text=_("URL-referenties naar ZAAKINFORMATIEOBJECTen."),
    )
    zaakobjecten = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        lookup_field="uuid",
        view_name="zaakobject-detail",
        source="zaakobject_set",
        help_text=_("URL-referenties naar ZAAKOBJECTen."),
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

    processobject = ProcessobjectSerializer(
        required=False,
        allow_null=True,
        help_text=_(
            "Specificatie van de attribuutsoort van het object, subject of gebeurtenis "
            " waarop, vanuit archiveringsoptiek, de zaak betrekking heeft en dat "
            "bepalend is voor de start van de archiefactietermijn."
        ),
    )

    inclusion_serializers = {
        # 1 level
        "zaaktype": "openzaak.components.catalogi.api.serializers.ZaakTypeSerializer",
        "hoofdzaak": "openzaak.components.zaken.api.serializers.ZaakSerializer",
        "deelzaken": "openzaak.components.zaken.api.serializers.ZaakSerializer",
        "eigenschappen": "openzaak.components.zaken.api.serializers.ZaakEigenschapSerializer",
        "status": "openzaak.components.zaken.api.serializers.StatusSerializer",
        "resultaat": "openzaak.components.zaken.api.serializers.ResultaatSerializer",
        "rollen": "openzaak.components.zaken.api.serializers.RolSerializer",
        "zaakinformatieobjecten": "openzaak.components.zaken.api.serializers.ZaakInformatieObjectSerializer",
        "zaakobjecten": "openzaak.components.zaken.api.serializers.ZaakObjectSerializer",
        # 2 and 3 level
        "hoofdzaak.zaaktype": "openzaak.components.catalogi.api.serializers.ZaakTypeSerializer",
        "hoofdzaak.status": "openzaak.components.zaken.api.serializers.StatusSerializer",
        "hoofdzaak.status.statustype": "openzaak.components.catalogi.api.serializers.StatusTypeSerializer",
        "hoofdzaak.resultaat": "openzaak.components.zaken.api.serializers.ResultaatSerializer",
        "hoofdzaak.resultaat.resultaattype": "openzaak.components.catalogi.api.serializers.ResultaatTypeSerializer",
        "hoofdzaak.rollen": "openzaak.components.zaken.api.serializers.RolSerializer",
        "hoofdzaak.rollen.roltype": "openzaak.components.catalogi.api.serializers.RolTypeSerializer",
        "hoofdzaak.zaakinformatieobjecten": "openzaak.components.zaken.api.serializers.ZaakInformatieObjectSerializer",
        "hoofdzaak.zaakobjecten": "openzaak.components.zaken.api.serializers.ZaakObjectSerializer",
        "deelzaken.zaaktype": "openzaak.components.catalogi.api.serializers.ZaakTypeSerializer",
        "deelzaken.status": "openzaak.components.zaken.api.serializers.StatusSerializer",
        "deelzaken.status.statustype": "openzaak.components.catalogi.api.serializers.StatusTypeSerializer",
        "deelzaken.resultaat": "openzaak.components.zaken.api.serializers.ResultaatSerializer",
        "deelzaken.resultaat.resultaattype": "openzaak.components.catalogi.api.serializers.ResultaatTypeSerializer",
        "deelzaken.rollen": "openzaak.components.zaken.api.serializers.RolSerializer",
        "deelzaken.rollen.roltype": "openzaak.components.catalogi.api.serializers.RolTypeSerializer",
        "deelzaken.zaakinformatieobjecten": "openzaak.components.zaken.api.serializers.ZaakInformatieObjectSerializer",
        "deelzaken.zaakobjecten": "openzaak.components.zaken.api.serializers.ZaakObjectSerializer",
        "eigenschappen.eigenschap": "openzaak.components.catalogi.api.serializers.EigenschapSerializer",
        "status.statustype": "openzaak.components.catalogi.api.serializers.StatusTypeSerializer",
        "resultaat.resultaattype": "openzaak.components.catalogi.api.serializers.ResultaatTypeSerializer",
        "rollen.roltype": "openzaak.components.catalogi.api.serializers.RolTypeSerializer",
        # we can't show 'zaakinformatieobjecten.informatieobject' because it's the resource from another API
    }

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
            "communicatiekanaal_naam",
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
            "rollen",
            "status",
            "zaakinformatieobjecten",
            "zaakobjecten",
            # Writable inline resource, as opposed to eigenschappen for demo
            # purposes. Eventually, we need to choose one form.
            "kenmerken",
            # Archiving
            "archiefnominatie",
            "archiefstatus",
            "archiefactiedatum",
            "resultaat",
            "opdrachtgevende_organisatie",
            "processobjectaard",
            "startdatum_bewaartermijn",
            "processobject",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaaktype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("ZaakType", settings.ZTC_API_STANDARD),
                    LooseFkIsImmutableValidator(),
                    PublishValidator(),
                ],
            },
            "zaakgeometrie": {
                "help_text": "Punt, lijn of (multi-)vlak geometrie-informatie, in GeoJSON."
            },
            "identificatie": {
                "required": False,
                "label": _("Identificatie"),
                "validators": [IsImmutableValidator()],
            },
            "einddatum": {"read_only": True, "allow_null": True},
            "communicatiekanaal": {
                "validators": [
                    ResourceValidator(
                        "CommunicatieKanaal", settings.REFERENTIELIJSTEN_API_STANDARD
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
                        settings.SELECTIELIJST_API_STANDARD,
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
        validators = [
            # Replace a default "unique together" constraint.
            UniekeIdentificatieValidator(),
            HoofdZaaktypeRelationValidator(),
            ZaakArchiveIOsArchivedValidator(),
            HoofdZaaktypeRelationValidator(),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(BetalingsIndicatie)
        fields["betalingsindicatie"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefstatus)
        fields["archiefstatus"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        fields["archiefnominatie"].help_text += f"\n\n{value_display_mapping}"

        return fields

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
            validated_data["vertrouwelijkheidaanduiding"] = (
                zaaktype.vertrouwelijkheidaanduiding
            )

        # set by the ZaakViewSet via create and get_serializer_context
        if generated_identificatie := self.context["generated_identificatie"]:
            validated_data.update(
                {
                    "identificatie_ptr": generated_identificatie,
                    "identificatie": generated_identificatie.identificatie,
                }
            )

        obj = super().create(validated_data)
        track_object_serializer(obj, self)

        # ⚡️ - a just created zaak cannot have a result, so we can avoid this DB query
        # by assigning the descriptor already
        obj.resultaat = None
        # ⚡️ - avoid status query for just created zaak
        obj.current_status_uuid = None

        # ⚡️ - on create, we _know_ that there are no existing relations yet (i.e.
        # objects that are related TO the zaak being created), so we can avoid doing
        # the queries to look up related objects for serialization by doing a .none()
        # query. kenmerken & relevant_andere_zaken can be written as inline resources,
        # so we can't guarantee these would be empty
        empty_relation_fields = (
            "eigenschappen",
            "deelzaken",
        )
        for field in empty_relation_fields:
            # point to the .none() queryset for output serialization
            self.fields[field].source_attrs.append("none")

        return obj


class GeoWithinSerializer(serializers.Serializer):
    within = GeometryField(required=False)


class ZaakZoekSerializer(serializers.Serializer):
    zaakgeometrie = GeoWithinSerializer(required=False)
    uuid__in = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text=_("Array of unieke resource identifiers (UUID4)"),
    )
    zaaktype__in = serializers.ListField(
        child=FKOrServiceUrlField(),
        required=False,
        help_text=_("Array van zaaktypen."),
    )
    zaaktype__not_in = serializers.ListField(
        child=FKOrServiceUrlField(),
        required=False,
        help_text=mark_experimental("Array van zaaktypen."),
    )

    class Meta:
        model = Zaak


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
            "indicatie_laatst_gezette_status",
            "gezetdoor",
            "zaakinformatieobjecten",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Status.objects.all(),
                fields=("zaak", "datum_status_gezet"),
            ),
            CorrectZaaktypeValidator("statustype"),
            EndStatusIOsUnlockedValidator(),
            EndStatusIOsIndicatieGebruiksrechtValidator(),
            StatusRolValidator(),
            ZaakArchiefStatusValidator(),
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
                    LooseFkResourceValidator("StatusType", settings.ZTC_API_STANDARD),
                ],
            },
            "indicatie_laatst_gezette_status": {
                "read_only": True,
                "help_text": _(
                    "Het gegeven is afleidbaar uit de historie van de attribuutsoort Datum "
                    "status gezet van van alle statussen bij de desbetreffende zaak."
                ),
            },
            "gezetdoor": {"lookup_field": "uuid"},
            "zaakinformatieobjecten": {
                "lookup_field": "uuid",
                "read_only": True,
                "many": True,
                "help_text": _("URL-referenties naar ZAAKINFORMATIEOBJECTen."),
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
            # zaak.einddatum is date, but status.datum_status_gezet is a datetime with tz support
            # durin validation step 'datum_status_gezet' was already converted to the
            # default timezone (UTC).
            # We want to take into consideration the client timezone before saving 'zaak.einddatum',
            # therefore we convert 'datum_status_gezet' back to the client timezone before taking its
            # date part.
            local_datum_status_gezet = parse_datetime(
                self.initial_data["datum_status_gezet"]
            )
            zaak.einddatum = local_datum_status_gezet.date()
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

            # Archiving: Calculate brondatum if it's not filled
            if not zaak.startdatum_bewaartermijn:
                zaak.startdatum_bewaartermijn = brondatum_calculator.brondatum
                if zaak.startdatum_bewaartermijn is not None:
                    _zaak_fields_changed.append("startdatum_bewaartermijn")

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
        choices=[(force_str(value), key) for key, value in RelatieAarden.choices],
    )
    informatieobject = EnkelvoudigInformatieObjectField(
        validators=[
            LooseFkIsImmutableValidator(instance_path="canonical"),
            LooseFkResourceValidator(
                "EnkelvoudigInformatieObject", settings.DRC_API_STANDARD
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
            "vernietigingsdatum",
            "status",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=ZaakInformatieObject.objects.all(),
                fields=["zaak", "informatieobject"],
            ),
            ObjecttypeInformatieobjecttypeRelationValidator(),
            ZaakArchiefStatusValidator(),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid", "validators": [IsImmutableValidator()]},
            "status": {"lookup_field": "uuid"},
        }

    def create(self, validated_data):
        with transaction.atomic():
            zio = super().create(validated_data)

        # we now expect to be in autocommit mode, i.e. - the transaction before has been
        # committed to the database as well. This makes it so that the remote DRC can
        # actually retrieve this ZIO we just created, to validate that we did indeed
        # create the relation information on our end.
        # XXX: would be nice to change the standard to rely on notifications for this
        # sync-machinery

        # Can't actually make the assertion because tests run in atomic transactions
        # assert (
        #     transaction.get_autocommit()
        # ), "Expected to be in autocommit mode at this point"

        # local FK or CMIS - nothing to do -> our signals create the OIO
        if settings.CMIS_ENABLED or zio.informatieobject.pk:
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
                    ).format(exception=exception)
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
    zaak = serializers.HyperlinkedRelatedField(
        queryset=Zaak.objects.all(),
        view_name="zaak-detail",
        lookup_field="uuid",
        validators=[IsImmutableValidator()],
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("url", "uuid", "zaak", "eigenschap", "naam", "waarde")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "naam": {"source": "_naam", "read_only": True},
            "eigenschap": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("Eigenschap", settings.ZTC_API_STANDARD),
                    LooseFkIsImmutableValidator(),
                ],
            },
        }
        validators = [
            CorrectZaaktypeValidator("eigenschap"),
            ZaakArchiefStatusValidator(),
            ZaakEigenschapValueValidator(),
        ]

    def validate(self, attrs):
        super().validate(attrs)

        # assign _naam only when creating zaak eigenschap
        if not self.instance:
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


class ContactPersoonRolSerializer(GegevensGroepSerializer):
    class Meta:
        model = Rol
        gegevensgroep = "contactpersoon_rol"


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
        same_model=False,
    )
    contactpersoon_rol = ContactPersoonRolSerializer(
        allow_null=True,
        required=False,
        help_text=_(
            "De gegevens van de persoon die anderen desgevraagd in contact brengt "
            "met medewerkers van de BETROKKENE, een NIET-NATUURLIJK PERSOON of "
            "VESTIGING zijnde, of met BETROKKENE zelf, een NATUURLIJK PERSOON zijnde "
            ", vanuit het belang van BETROKKENE in haar ROL bij een ZAAK."
        ),
    )

    class Meta:
        model = Rol
        fields = (
            "url",
            "uuid",
            "zaak",
            "betrokkene",
            "betrokkene_type",
            "afwijkende_naam_betrokkene",
            "roltype",
            "omschrijving",
            "omschrijving_generiek",
            "roltoelichting",
            "registratiedatum",
            "indicatie_machtiging",
            "contactpersoon_rol",
            "statussen",
            "begin_geldigheid",
            "einde_geldigheid",
        )
        validators = [
            RolOccurenceValidator(RolOmschrijving.initiator, max_amount=1),
            RolOccurenceValidator(RolOmschrijving.zaakcoordinator, max_amount=1),
            CorrectZaaktypeValidator("roltype"),
            ZaakArchiefStatusValidator(),
            RolIndicatieMachtigingValidator(),
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
                    LooseFkResourceValidator("RolType", settings.ZTC_API_STANDARD),
                    LooseFkIsImmutableValidator(),
                ],
                "help_text": get_help_text("zaken.Rol", "roltype"),
            },
            "statussen": {
                "lookup_field": "uuid",
                "read_only": True,
                "help_text": _(
                    "De BETROKKENE die in zijn/haar ROL in een ZAAK heeft geregistreerd "
                    "dat STATUSsen in die ZAAK bereikt zijn."
                ),
            },
        }

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(IndicatieMachtiging)
        fields["indicatie_machtiging"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolTypes)
        fields["betrokkene_type"].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RolOmschrijving)
        fields["omschrijving_generiek"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        betrokkene = validated_attrs.get("betrokkene", None)
        betrokkene_identificatie = validated_attrs.get("betrokkene_identificatie", None)

        if not betrokkene and not betrokkene_identificatie:
            raise serializers.ValidationError(
                _("betrokkene or betrokkeneIdentificatie must be provided"),
                code="invalid-betrokkene",
            )

        if (begin_geldigheid := validated_attrs.get("begin_geldigheid")) and (
            einde_geldigheid := validated_attrs.get("einde_geldigheid")
        ):
            if einde_geldigheid < begin_geldigheid:
                raise serializers.ValidationError(
                    {
                        "einde_geldigheid": _(
                            "`eindeGeldigheid` date cannot be before `beginGeldigheid` date"
                        )
                    },
                    code="einde-geldigheid-before-begin-geldigheid",
                )

        return validated_attrs

    @transaction.atomic
    def create(self, validated_data):
        group_data = validated_data.pop("betrokkene_identificatie", None)
        contactpersoon_rol = validated_data.pop("contactpersoon_rol", None)

        rol = super().create(validated_data)

        discriminated_serializer = self.discriminator.mapping[
            validated_data["betrokkene_type"]
        ]
        assert isinstance(discriminated_serializer, serializers.ModelSerializer)

        if group_data:
            serializer = discriminated_serializer.fields["betrokkene_identificatie"]
            group_data["rol"] = rol
            serializer.create(group_data)

        if contactpersoon_rol:
            rol.contactpersoon_rol = contactpersoon_rol
            rol.save()

        return rol

    @transaction.atomic
    def update(self, instance, validated_data):
        group_data = validated_data.pop("betrokkene_identificatie", None)
        contactpersoon_rol = validated_data.pop("contactpersoon_rol", None)

        # delete the existing betrokkene_identificatie instance
        if not instance.betrokkene:
            instance.betrokkene_identificatie.delete()

        rol = super().update(instance, validated_data)

        discriminated_serializer = self.discriminator.mapping[
            validated_data["betrokkene_type"]
        ]
        assert isinstance(discriminated_serializer, serializers.ModelSerializer)

        # recreate betrokkene_identificatie
        if group_data:
            serializer = discriminated_serializer.fields["betrokkene_identificatie"]
            group_data["rol"] = rol
            serializer.create(group_data)

        if contactpersoon_rol:
            rol.contactpersoon_rol = contactpersoon_rol
            rol.save()

        return rol


class ResultaatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Resultaat
        fields = ("url", "uuid", "zaak", "resultaattype", "toelichting")
        validators = [
            CorrectZaaktypeValidator("resultaattype"),
            ZaakArchiefStatusValidator(),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "resultaattype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator(
                        "ResultaatType", settings.ZTC_API_STANDARD
                    ),
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
                    LooseFkResourceValidator("Besluit", settings.BRC_API_STANDARD),
                ],
            },
        }
        validator = [ZaakArchiefStatusValidator()]

    def create(self, validated_data):
        validated_data["zaak"] = self.context["parent_object"]
        return super().create(validated_data)


class ZaakContactMomentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ZaakContactMoment
        fields = ("url", "uuid", "zaak", "contactmoment")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "contactmoment": {
                "validators": [
                    ResourceValidator(
                        "ContactMoment", settings.CMC_API_STANDARD, get_auth=get_auth
                    )
                ]
            },
        }
        validators = [ZaakArchiefStatusValidator()]

    def create(self, validated_data):
        with transaction.atomic():
            zaakcontactmoment = super().create(validated_data)

        # we now expect to be in autocommit mode, i.e. - the transaction before has been
        # committed to the database as well. This makes it so that the remote
        # Contactmomenten API can actually retrieve this ZaakContactmomenten we just
        # created, to validate that we did indeed create the relation information on our
        # end.

        # we know that we got valid URLs in the initial data
        contactmoment_url = self.initial_data["contactmoment"]
        zaak_url = self.initial_data["zaak"]

        # manual transaction management - contactmomenten API checks that the
        # ZaakContactMoment exists, so that transaction must be committed.
        # If it fails in any other way, we need to handle that by rolling back
        # the ZaakContactMoment creation.
        try:
            response = create_remote_objectcontactmoment(contactmoment_url, zaak_url)
        except Exception as exception:
            zaakcontactmoment.delete()
            raise serializers.ValidationError(
                {
                    "contactmoment": _(
                        "Could not create remote relation: {exception}"
                    ).format(exception=exception)
                },
                code="pending-relations",
            )
        else:
            zaakcontactmoment._objectcontactmoment = response["url"]
            zaakcontactmoment.save()

        return zaakcontactmoment


class ZaakVerzoekSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ZaakVerzoek
        fields = ("url", "uuid", "zaak", "verzoek")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid"},
            "verzoek": {"validators": [verzoek_validator]},
        }
        validators = [ZaakArchiefStatusValidator()]

    def create(self, validated_data):
        with transaction.atomic():
            zaakverzoek = super().create(validated_data)

        # we now expect to be in autocommit mode, i.e. - the transaction before has been
        # committed to the database as well. This makes it so that the remote
        # Verzoeken API can actually retrieve this ZaakVerzoek we just
        # created, to validate that we did indeed create the relation information on our
        # end.

        # we know that we got valid URLs in the initial data
        verzoek_url = self.initial_data["verzoek"]
        zaak_url = self.initial_data["zaak"]

        # manual transaction management - verzoeken API checks that the
        # ZaakVerzoek exists, so that transaction must be committed.
        # If it fails in any other way, we need to handle that by rolling back
        # the ZaakVerzoek creation.
        try:
            response = create_remote_objectverzoek(verzoek_url, zaak_url)
        except Exception as exception:
            zaakverzoek.delete()
            raise serializers.ValidationError(
                {
                    "verzoek": _(
                        "Could not create remote relation: {exception}"
                    ).format(exception=exception)
                },
                code="pending-relations",
            )
        else:
            zaakverzoek._objectverzoek = response["url"]
            zaakverzoek.save()

        return zaakverzoek
