# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer
from vng_api_common.utils import get_help_text

from ...models import ZaakObjectType
from ..validators import ZaakTypeConceptValidator


class ZaakObjectTypeSerializer(HyperlinkedModelSerializer):
    zaaktype_identificatie = serializers.SlugRelatedField(
        source="zaaktype",
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
    )
    catalogus = serializers.HyperlinkedRelatedField(
        view_name="catalogus-detail",
        source="zaaktype.catalogus",
        read_only=True,
        lookup_field="uuid",
        help_text=get_help_text("catalogi.ZaakType", "catalogus"),
    )

    class Meta:
        model = ZaakObjectType
        fields = (
            "url",
            "ander_objecttype",
            "objecttype",
            "relatie_omschrijving",
            "zaaktype",
            "zaaktype_identificatie",
            "resultaattypen",
            "statustypen",
            "catalogus",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "zaaktype": {"lookup_field": "uuid"},
            "resultaattypen": {
                "lookup_field": "uuid",
                "read_only": True,
                "many": True,
                "help_text": _("URL-referenties naar de RESULTAATTYPEN."),
            },
            "statustypen": {
                "lookup_field": "uuid",
                "read_only": True,
                "many": True,
                "help_text": _("URL-referenties naar de STATUSTYPEN."),
            },
            "catalogus": {"lookup_field": "uuid"},
        }
        validators = [ZaakTypeConceptValidator()]
