# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from ...models import Catalogus


class CatalogusSerializer(serializers.HyperlinkedModelSerializer):
    zaaktypen = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="zaaktype_set",
        view_name="zaaktype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar ZAAKTYPEn die in deze CATALOGUS worden ontsloten."
        ),
    )

    besluittypen = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="besluittype_set",
        view_name="besluittype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar BESLUITTYPEn die in deze CATALOGUS worden ontsloten."
        ),
    )

    informatieobjecttypen = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="informatieobjecttype_set",
        view_name="informatieobjecttype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar INFORMATIEOBJECTTYPEn die in deze CATALOGUS worden ontsloten."
        ),
    )

    class Meta:
        model = Catalogus
        fields = (
            "url",
            "domein",
            "rsin",
            "contactpersoon_beheer_naam",
            "contactpersoon_beheer_telefoonnummer",
            "contactpersoon_beheer_emailadres",
            "zaaktypen",
            "besluittypen",
            "informatieobjecttypen",
        )
        extra_kwargs = {"url": {"lookup_field": "uuid"}}
