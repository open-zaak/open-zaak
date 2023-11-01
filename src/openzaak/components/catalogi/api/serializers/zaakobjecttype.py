# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer
from vng_api_common.utils import get_help_text

from ...models import ZaakObjectType
from ..validators import (
    RelationZaaktypeValidator,
    StartBeforeEndValidator,
    ZaakTypeConceptValidator,
)


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
        model = ZaakObjectType
        fields = (
            "url",
            "ander_objecttype",
            "objecttype",
            "relatie_omschrijving",
            "zaaktype",
            "zaaktype_identificatie",
            "resultaattypen",
            "statustype",
            "catalogus",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
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
            "statustype": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
        }
        validators = [
            ZaakTypeConceptValidator(),
            RelationZaaktypeValidator("statustype"),
            StartBeforeEndValidator(),
        ]
