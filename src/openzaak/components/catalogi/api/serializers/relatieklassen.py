# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.serializers import add_choice_values_help_text

from ...constants import RichtingChoices
from ...models import ZaakTypeInformatieObjectType
from ..validators import ZaakTypeInformatieObjectTypeCatalogusValidator


class ZaakTypeInformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Represent a ZaakTypeInformatieObjectType.

    Relatie met informatieobjecttype dat relevant is voor zaaktype.
    """

    class Meta:
        model = ZaakTypeInformatieObjectType
        fields = (
            "url",
            "zaaktype",
            "informatieobjecttype",
            "volgnummer",
            "richting",
            "statustype",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        self.fields["richting"].help_text += f"\n\n{value_display_mapping}"

    def validate(self, attrs):
        super().validate(attrs)

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
