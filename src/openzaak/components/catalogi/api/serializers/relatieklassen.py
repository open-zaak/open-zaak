# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.utils import get_help_text

from openzaak.utils.validators import UniqueTogetherValidator

from ...constants import RichtingChoices
from ...models import ZaakTypeInformatieObjectType
from ..validators import ZaakTypeInformatieObjectTypeCatalogusValidator, is_force_write


class ZaakTypeInformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Represent a ZaakTypeInformatieObjectType.

    Relatie met informatieobjecttype dat relevant is voor zaaktype.
    """

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

    class Meta:
        model = ZaakTypeInformatieObjectType
        fields = (
            "url",
            "zaaktype",
            "zaaktype_identificatie",
            "informatieobjecttype",
            "volgnummer",
            "richting",
            "statustype",
            "catalogus",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "zaaktype": {"lookup_field": "uuid"},
            "informatieobjecttype": {"lookup_field": "uuid"},
            "statustype": {"lookup_field": "uuid"},
        }
        validators = [
            ZaakTypeInformatieObjectTypeCatalogusValidator(),
            UniqueTogetherValidator(
                queryset=ZaakTypeInformatieObjectType.objects.all(),
                fields=["zaaktype", "volgnummer"],
            ),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        fields["richting"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate(self, attrs):
        super().validate(attrs)

        # New in Catalogi 1.2: allow concept update for a specific scope
        if is_force_write(self):
            return attrs

        if self.instance:
            zaaktype = attrs.get("zaaktype") or self.instance.zaaktype
            informatieobjecttype = (
                attrs.get("informatieobjecttype") or self.instance.informatieobjecttype
            )

            if not (zaaktype.concept or informatieobjecttype.concept):
                message = _("Objects related to non-concept objects can't be updated")
                raise serializers.ValidationError(message, code="non-concept-relation")
        else:
            zaaktype = attrs.get("zaaktype")
            informatieobjecttype = attrs.get("informatieobjecttype")

            if not (zaaktype.concept or informatieobjecttype.concept):
                message = _(
                    "Creating relations between non-concept objects is forbidden"
                )
                raise serializers.ValidationError(message, code="non-concept-relation")

        return attrs
