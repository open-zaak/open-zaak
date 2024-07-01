# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.utils import get_help_text

from openzaak.utils.validators import UniqueTogetherValidator

from ...constants import FormaatChoices
from ...models import Eigenschap, EigenschapSpecificatie
from ..validators import (
    RelationZaaktypeValidator,
    StartBeforeEndValidator,
    ZaakTypeConceptValidator,
)


class EigenschapSpecificatieSerializer(serializers.ModelSerializer):
    class Meta:
        model = EigenschapSpecificatie
        fields = ("groep", "formaat", "lengte", "kardinaliteit", "waardenverzameling")

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(FormaatChoices)
        fields["formaat"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate(self, attrs):
        instance = EigenschapSpecificatie(**attrs)
        instance.clean()
        return attrs


class EigenschapSerializer(
    NestedCreateMixin, NestedUpdateMixin, serializers.HyperlinkedModelSerializer
):
    specificatie = EigenschapSpecificatieSerializer(
        source="specificatie_van_eigenschap"
    )
    catalogus = serializers.HyperlinkedRelatedField(
        view_name="catalogus-detail",
        source="zaaktype.catalogus",
        read_only=True,
        lookup_field="uuid",
        help_text=get_help_text("catalogi.ZaakType", "catalogus"),
    )
    zaaktype_identificatie = serializers.SlugRelatedField(
        source="zaaktype",
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
    )
    begin_object = serializers.DateField(
        source="datum_begin_geldigheid",
        read_only=True,
        help_text=_("De datum waarop de eerst versie van het object ontstaan is."),
    )
    einde_object = serializers.DateField(
        source="datum_einde_geldigheid",
        read_only=True,
        help_text=_("De datum van de aller laatste versie van het object."),
    )

    class Meta:
        model = Eigenschap
        fields = (
            "url",
            "naam",
            "definitie",
            "specificatie",
            "toelichting",
            "zaaktype",
            "zaaktype_identificatie",
            "catalogus",
            "statustype",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "naam": {"source": "eigenschapnaam"},
            "zaaktype": {"lookup_field": "uuid"},
            "statustype": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
        }
        validators = [
            ZaakTypeConceptValidator(),
            UniqueTogetherValidator(
                queryset=Eigenschap.objects.all(),
                fields=["zaaktype", "naam"],
            ),
            RelationZaaktypeValidator("statustype"),
            StartBeforeEndValidator(),
        ]

    def _get_serializer_for_field(self, field, **kwargs):
        # workaround for drf-writable-nested. it looks up the instance by PK, but we don't
        # expose that in the serializer at all.
        if field.field_name == "specificatie" and self.instance:
            kwargs["instance"] = self.instance.specificatie_van_eigenschap
        return super()._get_serializer_for_field(field, **kwargs)
