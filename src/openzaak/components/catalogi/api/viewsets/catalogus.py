# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import Catalogus
from ..filters import CatalogusFilter
from ..scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..serializers import CatalogusSerializer


class CatalogusViewSet(
    CheckQueryParamsMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet
):
    """
    Opvragen en bewerken van CATALOGUSsen.

    De verzameling van ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn voor
    een domein die als één geheel beheerd wordt.

    create:
    Maak een CATALOGUS aan.

    Maak een CATALOGUS aan.

    list:
    Alle CATALOGUSsen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke CATALOGUS opvragen.

    Een specifieke CATALOGUS opvragen.

    update:
    Werk een CATALOGUS in zijn geheel bij.

    Werk een CATALOGUS in zijn geheel bij.

    partial_update:
    Werk een CATALOGUS deels bij.

    Werk een CATALOGUS deels bij.

    destroy:
    Verwijder een CATALOGUS.

    Verwijder een CATALOGUS. Dit kan alleen als er geen onderliggende
    ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn zijn.
    """

    queryset = (
        Catalogus.objects.all()
        .prefetch_related("besluittype_set", "zaaktype_set", "informatieobjecttype_set")
        .order_by("-pk")
    )
    serializer_class = CatalogusSerializer
    filter_class = CatalogusFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE,
    }
