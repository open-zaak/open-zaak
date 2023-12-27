# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import Catalogus
from ..filters import CatalogusFilter
from ..scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..serializers import CatalogusSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Alle CATALOGUSsen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke CATALOGUS opvragen.",
        description="Een specifieke CATALOGUS opvragen.",
    ),
    create=extend_schema(
        summary="Maak een CATALOGUS aan.", description="Maak een CATALOGUS aan."
    ),
    update=extend_schema(
        summary="Werk een CATALOGUS in zijn geheel bij.",
        description="Werk een CATALOGUS in zijn geheel bij.",
    ),
    partial_update=extend_schema(
        summary="Werk een CATALOGUS deels bij.",
        description="Werk een CATALOGUS deels bij.",
    ),
    destroy=extend_schema(
        summary="Verwijder een CATALOGUS.",
        description=(
            "Verwijder een CATALOGUS. Dit kan alleen als er geen onderliggende "
            "ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn zijn."
        ),
    ),
)
@conditional_retrieve()
class CatalogusViewSet(
    CheckQueryParamsMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet
):
    """
    Opvragen en bewerken van CATALOGUSsen.
    """

    queryset = (
        Catalogus.objects.all()
        .prefetch_related("besluittype_set", "zaaktype_set", "informatieobjecttype_set")
        .order_by("-pk")
    )
    serializer_class = CatalogusSerializer
    filter_class = CatalogusFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE,
    }
