# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.utils import get_help_text

from ...models import StatusType
from ..validators import ZaakTypeConceptValidator


class StatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    is_eindstatus = serializers.BooleanField(
        read_only=True,
        help_text=_(
            "Geeft aan dat dit STATUSTYPE een eindstatus betreft. Dit "
            "gegeven is afgeleid uit alle STATUSTYPEn van dit ZAAKTYPE "
            "met het hoogste volgnummer."
        ),
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

    class Meta:
        model = StatusType
        fields = (
            "url",
            "omschrijving",
            "omschrijving_generiek",
            "statustekst",
            "zaaktype",
            "zaaktype_identificatie",
            "volgnummer",
            "is_eindstatus",
            "informeren",
            "catalogus",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "statustype_omschrijving"},
            "omschrijving_generiek": {"source": "statustype_omschrijving_generiek"},
            "volgnummer": {"source": "statustypevolgnummer"},
            "zaaktype": {"lookup_field": "uuid"},
        }
        validators = [ZaakTypeConceptValidator()]
