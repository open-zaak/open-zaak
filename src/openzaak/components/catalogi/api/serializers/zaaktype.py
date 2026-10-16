# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from uuid import UUID

from django.conf import settings
from django.db.models import Manager
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework.serializers import (
    DateField,
    HyperlinkedModelSerializer,
    ListSerializer,
    ModelSerializer,
    SerializerMethodField,
    SlugRelatedField,
)
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    CachedHyperlinkedRelatedField,
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)

from openzaak.utils.validators import ResourceValidator

from ...constants import AardRelatieChoices, RichtingChoices
from ...models import BesluitType, ZaakType, ZaakTypenRelatie
from ..validators import (
    BronZaakTypeValidator,
    ConceptUpdateValidator,
    DeelzaaktypeCatalogusValidator,
    GeldigheidPublishValidator,
    GeldigheidValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
    NonZeroRelativeDeltaValidator,
    RelationCatalogValidator,
    VerlengingsValidator,
    ZaakTypeRelationsPublishValidator,
)


class ReferentieProcesSerializer(GegevensGroepSerializer):
    class Meta:
        model = ZaakType
        gegevensgroep = "referentieproces"


ZAAKTYPE_IDENTIFICATIE_CACHE_KEY = "_zaaktype_identificatie_cache"


def _get_uuid_from_url(url: str) -> UUID | None:
    try:
        return UUID(url.rstrip("/").rsplit("/", 1)[-1])
    except ValueError:
        return None


class ZaakTypenRelatieListSerializer(ListSerializer):
    """
    Resolve the identificaties of all related ZAAKTYPEs in a single query.

    ``gerelateerd_zaaktype`` is a plain URL which may point to an external ZTC, so
    it can't be prefetched like a regular relation.
    """

    def to_representation(self, data):
        relaties = data.all() if isinstance(data, Manager) else list(data)
        cache = self.context.setdefault(ZAAKTYPE_IDENTIFICATIE_CACHE_KEY, {})

        uuids = {
            uuid
            for relatie in relaties
            if (uuid := _get_uuid_from_url(relatie.gerelateerd_zaaktype))
            and uuid not in cache
        }
        if uuids:
            found = dict(
                ZaakType.objects.filter(uuid__in=uuids).values_list(
                    "uuid", "identificatie"
                )
            )
            # also cache the misses (external zaaktypen) to avoid repeated lookups
            cache.update({uuid: found.get(uuid, "") for uuid in uuids})

        return super().to_representation(relaties)


class ZaakTypenRelatieSerializer(ModelSerializer):
    zaaktype_identificatie = SerializerMethodField(
        help_text=_("Identificatie van het gerelateerde zaaktype."),
    )

    class Meta:
        model = ZaakTypenRelatie
        list_serializer_class = ZaakTypenRelatieListSerializer
        fields = (
            "zaaktype",
            "zaaktype_identificatie",
            "aard_relatie",
            "toelichting",
        )
        extra_kwargs = {"zaaktype": {"source": "gerelateerd_zaaktype"}}

    @extend_schema_field(OpenApiTypes.STR)
    def get_zaaktype_identificatie(self, obj: ZaakTypenRelatie) -> str:
        """
        The identificatie is empty if the related ZAAKTYPE is not known locally.
        """
        uuid = _get_uuid_from_url(obj.gerelateerd_zaaktype)
        cache = self.context.get(ZAAKTYPE_IDENTIFICATIE_CACHE_KEY, {})
        return cache.get(uuid, "")

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(AardRelatieChoices)
        fields["aard_relatie"].help_text += f"\n\n{value_display_mapping}"

        return fields


class BronCatalogusSerializer(GegevensGroepSerializer):
    class Meta:
        model = ZaakType
        gegevensgroep = "broncatalogus"


class BronZaaktypeSerializer(GegevensGroepSerializer):
    class Meta:
        model = ZaakType
        gegevensgroep = "bronzaaktype"


class ZaakTypeSerializer(
    NestedGegevensGroepMixin,
    NestedCreateMixin,
    NestedUpdateMixin,
    HyperlinkedModelSerializer,
):
    referentieproces = ReferentieProcesSerializer(
        required=True,
        help_text=_("Het Referentieproces dat ten grondslag ligt aan dit ZAAKTYPE."),
    )

    gerelateerde_zaaktypen = ZaakTypenRelatieSerializer(
        many=True,
        source="zaaktypenrelaties",
        help_text="De ZAAKTYPEn van zaken die relevant zijn voor zaken van dit ZAAKTYPE.",
    )
    broncatalogus = BronCatalogusSerializer(
        allow_null=False,
        required=False,
        help_text=_("De CATALOGUS waaraan het ZAAKTYPE is ontleend."),
    )

    bronzaaktype = BronZaaktypeSerializer(
        allow_null=False,
        required=False,
        help_text=_(
            "Het ZAAKTYPE binnen de CATALOGUS waaraan dit ZAAKTYPE is ontleend."
        ),
    )

    # relations
    informatieobjecttypen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="informatieobjecttype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de INFORMATIEOBJECTTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    informatieobjecttype_omschrijving = SlugRelatedField(
        many=True,
        read_only=True,
        source="informatieobjecttypen",
        slug_field="omschrijving",
        help_text=_(
            "Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )

    statustypen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="statustype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de STATUSTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    resultaattypen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="resultaattype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de RESULTAATTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    eigenschappen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="eigenschap_set",
        view_name="eigenschap-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de EIGENSCHAPPEN die aanwezig moeten zijn in ZAKEN van dit ZAAKTYPE."
        ),
    )

    roltypen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="roltype_set",
        view_name="roltype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de ROLTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    besluittypen = CachedHyperlinkedRelatedField(
        many=True,
        label=_("heeft relevante besluittypen"),
        view_name="besluittype-detail",
        lookup_field="uuid",
        queryset=BesluitType.objects.all(),
        help_text=_(
            "URL-referenties naar de BESLUITTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    besluittype_omschrijving = SlugRelatedField(
        many=True,
        read_only=True,
        source="besluittypen",
        slug_field="omschrijving",
        help_text=_("Omschrijving van de aard van BESLUITen van het BESLUITTYPE."),
    )

    zaakobjecttypen = CachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="zaakobjecttype_set",
        view_name="zaakobjecttype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de ZAAKOBJECTTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )
    begin_object = DateField(
        read_only=True,
        help_text=_("De datum waarop de eerst versie van het object ontstaan is."),
    )
    einde_object = DateField(
        read_only=True,
        help_text=_("De datum van de aller laatste versie van het object."),
    )
    deelzaaktype_identificaties = SlugRelatedField(
        source="deelzaaktypen",
        many=True,
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificaties van de ZAAKTYPE(n) waaronder ZAAKen als "
            "deelzaak kunnen voorkomen bij ZAAKen van dit ZAAKTYPE."
        ),
    )
    inclusion_serializers = {
        "zaakobjecttypen": "openzaak.components.catalogi.api.serializers.ZaakObjectTypeSerializer",
        "catalogus": "openzaak.components.catalogi.api.serializers.CatalogusSerializer",
        "statustypen": "openzaak.components.catalogi.api.serializers.StatusTypeSerializer",
        "resultaattypen": "openzaak.components.catalogi.api.serializers.ResultaatTypeSerializer",
        "eigenschappen": "openzaak.components.catalogi.api.serializers.EigenschapSerializer",
        "informatieobjecttypen": "openzaak.components.catalogi.api.serializers.InformatieObjectTypeSerializer",
        "roltypen": "openzaak.components.catalogi.api.serializers.RolTypeSerializer",
        "besluittypen": "openzaak.components.catalogi.api.serializers.BesluitTypeSerializer",
        "deelzaaktypen": "openzaak.components.catalogi.api.serializers.ZaakTypeSerializer",
    }

    class Meta:
        model = ZaakType
        fields = (
            "url",
            "identificatie",
            "omschrijving",
            "omschrijving_generiek",
            "vertrouwelijkheidaanduiding",
            "doel",
            "aanleiding",
            "toelichting",
            "indicatie_intern_of_extern",
            "handeling_initiator",
            "onderwerp",
            "handeling_behandelaar",
            "doorlooptijd",
            "servicenorm",
            "opschorting_en_aanhouding_mogelijk",
            "verlenging_mogelijk",
            "verlengingstermijn",
            "trefwoorden",
            "publicatie_indicatie",
            "publicatietekst",
            "verantwoordingsrelatie",
            "producten_of_diensten",
            "selectielijst_procestype",
            "referentieproces",
            "concept",
            "verantwoordelijke",
            "broncatalogus",
            "bronzaaktype",
            # dates
            "begin_geldigheid",
            "einde_geldigheid",
            "versiedatum",
            "begin_object",
            "einde_object",
            # relations
            "catalogus",
            "statustypen",
            "resultaattypen",
            "eigenschappen",
            "informatieobjecttypen",
            "informatieobjecttype_omschrijving",
            "roltypen",
            "besluittypen",
            "besluittype_omschrijving",
            "deelzaaktypen",
            "deelzaaktype_identificaties",
            "gerelateerde_zaaktypen",
            "zaakobjecttypen",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "zaaktype_omschrijving"},
            "omschrijving_generiek": {"source": "zaaktype_omschrijving_generiek"},
            "catalogus": {"lookup_field": "uuid"},
            "doorlooptijd": {"source": "doorlooptijd_behandeling"},
            "servicenorm": {
                "source": "servicenorm_behandeling",
                "validators": [NonZeroRelativeDeltaValidator()],
            },
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
            "concept": {"read_only": True},
            "producten_of_diensten": {"required": True},
            "selectielijst_procestype": {
                "validators": [
                    ResourceValidator("ProcesType", settings.SELECTIELIJST_API_STANDARD)
                ]
            },
            "deelzaaktypen": {"lookup_field": "uuid"},
        }

        validators = [
            GeldigheidValidator("identificatie"),
            RelationCatalogValidator("besluittypen"),
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["besluittypen", "informatieobjecttypen"]),
            M2MConceptUpdateValidator(["besluittypen"]),
            DeelzaaktypeCatalogusValidator(),
            VerlengingsValidator(),
            BronZaakTypeValidator(),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        fields["indicatie_intern_of_extern"].help_text += f"\n\n{value_display_mapping}"

        return fields


class ZaakTypePublishSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ZaakType
        fields = ("concept",)
        validators = [
            ZaakTypeRelationsPublishValidator(),
            GeldigheidPublishValidator("identificatie"),
        ]
