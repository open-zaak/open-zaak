# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import ZaakObjectType
from ..filters import ZaakObjectTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ZaakObjectTypeSerializer
from .mixins import ZaakTypeConceptMixin

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKOBJECTTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAKOBJECTTYPE opvragen.",
        description="Een specifieke ZAAKOBJECTTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKOBJECTTYPE aan.",
        description="Maak een ZAAKOBJECTTYPE aan.",
    ),
    update=extend_schema(
        summary="Werk een ZAAKOBJECTTYPE in zijn geheel bij.",
        description="Werk een ZAAKOBJECTTYPE in zijn geheel bij.",
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKOBJECTTYPE deels bij.",
        description="Werk een ZAAKOBJECTTYPE deels bij.",
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKOBJECTTYPE.",
        description="Verwijder een ZAAKOBJECTTYPE.",
    ),
)
@conditional_retrieve()
class ZaakObjectTypeViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ZaakTypeConceptMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKOBJECTTYPEn.
    """

    queryset = (
        ZaakObjectType.objects.select_related(
            "zaaktype", "zaaktype__catalogus", "statustype"
        )
        .prefetch_related("resultaattypen")
        .order_by("-pk")
        .all()
    )
    serializer_class = ZaakObjectTypeSerializer
    filterset_class = ZaakObjectTypeFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
    }

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "zaakobjecttype_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "zaakobjecttype_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        super().perform_destroy(instance)
        logger.info(
            "zaakobjecttype_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )
