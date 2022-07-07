# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from openzaak.utils.validators import UniqueTogetherValidator

from ...constants import FormaatChoices
from ...models import Eigenschap, EigenschapSpecificatie
from ..validators import ZaakTypeConceptValidator


class EigenschapSpecificatieSerializer(serializers.ModelSerializer):
    class Meta:
        model = EigenschapSpecificatie
        fields = ("groep", "formaat", "lengte", "kardinaliteit", "waardenverzameling")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(FormaatChoices)
        self.fields["formaat"].help_text += f"\n\n{value_display_mapping}"

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

    class Meta:
        model = Eigenschap
        fields = ("url", "naam", "definitie", "specificatie", "toelichting", "zaaktype")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "naam": {"source": "eigenschapnaam"},
            "zaaktype": {"lookup_field": "uuid"},
        }
        validators = [
            ZaakTypeConceptValidator(),
            UniqueTogetherValidator(
                queryset=Eigenschap.objects.all(), fields=["zaaktype", "naam"],
            ),
        ]

    def _get_serializer_for_field(self, field, **kwargs):
        # workaround for drf-writable-nested. it looks up the instance by PK, but we don't
        # expose that in the serializer at all.
        if field.field_name == "specificatie" and self.instance:
            kwargs["instance"] = self.instance.specificatie_van_eigenschap
        return super()._get_serializer_for_field(field, **kwargs)
