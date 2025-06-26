# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import Catalogus
from ..filters import CatalogusFilter
from ..scopes import SCOPE_CATALOGI_READ, SCOPE_CATALOGI_WRITE
from ..serializers import CatalogusSerializer

logger = structlog.stdlib.get_logger(__name__)


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
)
@conditional_retrieve()
class CatalogusViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
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
    filterset_class = CatalogusFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
    }

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        logger.info(
            "catalogus_list_completed",
            user=str(request.user),
            result_count=len(response.data)
            if isinstance(response.data, list)
            else None,
            view=self.__class__.__name__,
        )
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        logger.info(
            "catalogus_retrieve_completed",
            user=str(request.user),
            uuid=kwargs.get("uuid"),
            view=self.__class__.__name__,
        )
        return response

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(
            "catalogus_create_completed",
            user=str(request.user),
            created_id=response.data.get("uuid")
            if isinstance(response.data, dict)
            else None,
            view=self.__class__.__name__,
        )
        return response
