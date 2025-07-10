# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import DatabaseError, transaction

import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.components.catalogi.models import Eigenschap
from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ..filters import EigenschapFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import EigenschapSerializer
from .mixins import ZaakTypeConceptMixin

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle EIGENSCHAPpen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke EIGENSCHAP opvragen.",
        description="Een specifieke EIGENSCHAP opvragen.",
    ),
    create=extend_schema(
        summary="Maak een EIGENSCHAP aan.",
        description=(
            "Maak een EIGENSCHAP aan. Dit kan alleen als het bijbehorende ZAAKTYPE een "
            "concept betreft."
        ),
    ),
    update=extend_schema(
        summary="Werk een EIGENSCHAP in zijn geheel bij.",
        description=(
            "Werk een EIGENSCHAP in zijn geheel bij. Dit kan alleen als het "
            "bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een EIGENSCHAP deels bij.",
        description=(
            "Werk een EIGENSCHAP deels bij. Dit kan alleen als het bijbehorende "
            "ZAAKTYPE een concept betreft."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een EIGENSCHAP.",
        description=(
            "Verwijder een EIGENSCHAP. Dit kan alleen als het bijbehorende ZAAKTYPE een "
            "concept betreft."
        ),
    ),
)
@conditional_retrieve()
class EigenschapViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ZaakTypeConceptMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van EIGENSCHAPpen van een ZAAKTYPE.

    Een relevant inhoudelijk gegeven dat bij ZAAKen van dit ZAAKTYPE
    geregistreerd moet kunnen worden en geen standaard kenmerk is van een zaak.
    """

    queryset = (
        Eigenschap.objects.all()
        .select_related(
            "specificatie_van_eigenschap", "zaaktype", "zaaktype__catalogus"
        )
        .order_by("-pk")
    )
    serializer_class = EigenschapSerializer
    filterset_class = EigenschapFilter
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
            "eigenschap_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "eigenschap_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        try:
            super().perform_destroy(instance)
        except DatabaseError as e:
            logger.error(
                "eigenschap_delete_failed",
                client_id=self.request.jwt_auth.client_id,
                uuid=uuid,
                error=str(e),
            )
            raise

        logger.info(
            "eigenschap_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )
