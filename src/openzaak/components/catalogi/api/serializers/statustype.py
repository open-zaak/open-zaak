# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from drf_writable_nested import NestedCreateMixin, NestedUpdateMixin
from rest_framework import serializers
from vng_api_common.utils import get_help_text

from ...models import CheckListItem, StatusType
from ..validators import StartBeforeEndValidator, ZaakTypeConceptValidator


class CheckListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckListItem
        fields = (
            "itemnaam",
            "toelichting",
            "vraagstelling",
            "verplicht",
        )


class StatusTypeSerializer(
    NestedCreateMixin, NestedUpdateMixin, serializers.HyperlinkedModelSerializer
):
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
    eigenschappen = serializers.HyperlinkedRelatedField(
        view_name="eigenschap-detail",
        many=True,
        read_only=True,
        lookup_field="uuid",
        help_text=_(
            "de EIGENSCHAPpen die verplicht een waarde moeten hebben gekregen, "
            "voordat een STATUS van dit STATUSTYPE kan worden gezet."
        ),
    )
    zaakobjecttypen = serializers.HyperlinkedRelatedField(
        view_name="zaakobjecttype-detail",
        many=True,
        read_only=True,
        lookup_field="uuid",
        help_text=_(
            "de ZAAKOBJECTTYPEN die verplicht een waarde moeten hebben gekregen, "
            "voordat een STATUS van dit STATUSTYPE kan worden gezet."
        ),
    )
    checklistitem_statustype = CheckListItemSerializer(
        required=False,
        many=True,
        source="checklistitem_set",
        help_text=_(
            "Te controleren aandachtspunt voorafgaand aan het bereiken "
            "van een status van het STATUSTYPE."
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
            "doorlooptijd",
            "toelichting",
            "checklistitem_statustype",
            "catalogus",
            "eigenschappen",
            "zaakobjecttypen",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "statustype_omschrijving"},
            "omschrijving_generiek": {"source": "statustype_omschrijving_generiek"},
            "volgnummer": {"source": "statustypevolgnummer"},
            "zaaktype": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
        }
        validators = [ZaakTypeConceptValidator(), StartBeforeEndValidator()]
