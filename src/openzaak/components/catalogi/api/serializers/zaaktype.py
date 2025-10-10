# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework.serializers import (
    DateField,
    HyperlinkedModelSerializer,
    ModelSerializer,
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
    RelationCatalogValidator,
    VerlengingsValidator,
    ZaakTypeRelationsPublishValidator,
)


class ReferentieProcesSerializer(GegevensGroepSerializer):
    class Meta:
        model = ZaakType
        gegevensgroep = "referentieproces"


class ZaakTypenRelatieSerializer(ModelSerializer):
    class Meta:
        model = ZaakTypenRelatie
        fields = ("zaaktype", "aard_relatie", "toelichting")
        extra_kwargs = {"zaaktype": {"source": "gerelateerd_zaaktype"}}

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
            "roltypen",
            "besluittypen",
            "deelzaaktypen",
            "gerelateerde_zaaktypen",
            "zaakobjecttypen",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "zaaktype_omschrijving"},
            "omschrijving_generiek": {"source": "zaaktype_omschrijving_generiek"},
            "catalogus": {"lookup_field": "uuid"},
            "doorlooptijd": {"source": "doorlooptijd_behandeling"},
            "servicenorm": {"source": "servicenorm_behandeling"},
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
