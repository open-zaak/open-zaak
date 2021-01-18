# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    HyperlinkedRelatedField,
    ModelSerializer,
)
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)
from vng_api_common.validators import ResourceValidator

from ...constants import AardRelatieChoices, RichtingChoices
from ...models import BesluitType, ZaakType, ZaakTypenRelatie
from ..validators import (
    ConceptUpdateValidator,
    DeelzaaktypeCatalogusValidator,
    M2MConceptCreateValidator,
    M2MConceptUpdateValidator,
    RelationCatalogValidator,
    ZaaktypeGeldigheidValidator,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(AardRelatieChoices)
        self.fields["aard_relatie"].help_text += f"\n\n{value_display_mapping}"


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

    informatieobjecttypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="informatieobjecttype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de INFORMATIEOBJECTTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    statustypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="statustype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de STATUSTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    resultaattypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="resultaattype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de RESULTAATTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    eigenschappen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="eigenschap_set",
        view_name="eigenschap-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de EIGENSCHAPPEN die aanwezig moeten zijn in ZAKEN van dit ZAAKTYPE."
        ),
    )

    roltypen = HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="roltype_set",
        view_name="roltype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar de ROLTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
    )

    besluittypen = HyperlinkedRelatedField(
        many=True,
        label=_("heeft relevante besluittypen"),
        view_name="besluittype-detail",
        lookup_field="uuid",
        queryset=BesluitType.objects.all(),
        help_text=_(
            "URL-referenties naar de BESLUITTYPEN die mogelijk zijn binnen dit ZAAKTYPE."
        ),
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
            "catalogus",
            "statustypen",
            "resultaattypen",
            "eigenschappen",
            "informatieobjecttypen",
            "roltypen",
            "besluittypen",
            "deelzaaktypen",
            "gerelateerde_zaaktypen",
            "begin_geldigheid",
            "einde_geldigheid",
            "versiedatum",
            "concept",
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
            "selectielijst_procestype": {
                "validators": [
                    ResourceValidator("ProcesType", settings.REFERENTIELIJSTEN_API_SPEC)
                ]
            },
            "deelzaaktypen": {"lookup_field": "uuid"},
        }

        validators = [
            ZaaktypeGeldigheidValidator(),
            RelationCatalogValidator("besluittypen"),
            ConceptUpdateValidator(),
            M2MConceptCreateValidator(["besluittypen", "informatieobjecttypen"]),
            M2MConceptUpdateValidator(["besluittypen", "informatieobjecttypen"]),
            DeelzaaktypeCatalogusValidator(),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        self.fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        self.fields[
            "indicatie_intern_of_extern"
        ].help_text += f"\n\n{value_display_mapping}"
