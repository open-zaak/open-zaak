# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import StatusType
from ..filters import StatusTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import StatusTypeSerializer
from .mixins import ZaakTypeConceptMixin

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle STATUSTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke STATUSTYPE opvragen.",
        description="Een specifieke STATUSTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een STATUSTYPE aan.",
        description=(
            "Maak een STATUSTYPE aan. Dit kan alleen als het bijbehorende ZAAKTYPE een "
            "concept betreft."
        ),
    ),
    update=extend_schema(
        summary="Werk een STATUSTYPE in zijn geheel bij.",
        description=(
            "Werk een STATUSTYPE in zijn geheel bij. Dit kan alleen als het "
            "bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een STATUSTYPE deels bij.",
        description=(
            "Werk een STATUSTYPE deels bij. Dit kan alleen als het bijbehorende "
            "ZAAKTYPE een concept betreft."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een STATUSTYPE.",
        description=(
            "Verwijder een STATUSTYPE. Dit kan alleen als het bijbehorende ZAAKTYPE een "
            "concept betreft."
        ),
    ),
)
@conditional_retrieve()
class StatusTypeViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ZaakTypeConceptMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van STATUSTYPEn van een ZAAKTYPE.

    Generieke aanduiding van de aard van een status.
    """

    queryset = (
        StatusType.objects.select_related("zaaktype", "zaaktype__catalogus")
        .prefetch_related(
            "zaaktype__statustypen",
            "eigenschappen",
            "zaakobjecttypen",
            "checklistitem_set",
        )
        .order_by("-pk")
        .all()
    )
    serializer_class = StatusTypeSerializer
    filterset_class = StatusTypeFilter
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
            "statustype_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "statustype_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        super().perform_destroy(instance)
        logger.info(
            "statustype_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )
