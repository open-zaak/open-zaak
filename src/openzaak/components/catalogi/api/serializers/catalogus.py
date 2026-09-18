# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from openzaak.utils.serializer_fields import (
    DeprecatedNamespaceCachedHyperlinkedRelatedField,
)
from openzaak.utils.serializers import DeprecatedNamespaceHyperlinkedModelSerializer

from ...models import Catalogus


class CatalogusSerializer(DeprecatedNamespaceHyperlinkedModelSerializer):
    zaaktypen = DeprecatedNamespaceCachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="zaaktype_set",
        view_name="zaken:zaaktype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar ZAAKTYPEn die in deze CATALOGUS worden ontsloten."
        ),
    )

    besluittypen = DeprecatedNamespaceCachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="besluittype_set",
        view_name="zaken:besluittype-detail",
        lookup_field="uuid",
        help_text=_(
            "URL-referenties naar BESLUITTYPEn die in deze CATALOGUS worden ontsloten."
        ),
    )

    informatieobjecttypen = DeprecatedNamespaceCachedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        source="informatieobjecttype_set",
        view_name="documenten:informatieobjecttype-detail",
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
            "naam",
            "versie",
            "begindatum_versie",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid", "view_name": "zaken:catalogus-detail"}
        }
