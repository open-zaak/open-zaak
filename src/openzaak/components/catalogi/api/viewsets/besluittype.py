# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import DatabaseError, transaction

import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import COMMON_ERROR_RESPONSES, VALIDATION_ERROR_RESPONSES

from ...models import BesluitType
from ..filters import BesluitTypeFilter
from ..kanalen import KANAAL_BESLUITTYPEN
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import BesluitTypePublishSerializer, BesluitTypeSerializer
from .mixins import ConceptMixin, M2MConceptDestroyMixin

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle BESLUITTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke BESLUITTYPE opvragen.",
        description="Een specifieke BESLUITTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een BESLUITTYPE aan.", description="Maak een BESLUITTYPE aan."
    ),
    update=extend_schema(
        summary="Werk een BESLUITTYPE in zijn geheel bij.",
        description=(
            "Werk een BESLUITTYPE in zijn geheel bij. Dit kan alleen als het een concept "
            "betreft."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een BESLUITTYPE deels bij.",
        description="Werk een BESLUITTYPE deels bij. Dit kan alleen als het een concept betreft.",
    ),
    destroy=extend_schema(
        summary="Verwijder een BESLUITTYPE.",
        description="Verwijder een BESLUITTYPE. Dit kan alleen als het een concept betreft.",
    ),
)
@conditional_retrieve()
class BesluitTypeViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ConceptMixin,
    M2MConceptDestroyMixin,
    NotificationViewSetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van BESLUITTYPEn nodig voor BESLUITEN in de Besluiten
    API.

    Alle BESLUITTYPEn van de besluiten die het resultaat kunnen zijn van het
    zaakgericht werken van de behandelende organisatie(s).

    publish:
    Publiceer het concept BESLUITTYPE.

    Publiceren van het besluittype zorgt ervoor dat dit in een Besluiten API kan gebruikt
    worden. Na het publiceren van een besluittype zijn geen inhoudelijke wijzigingen
    meer mogelijk. Indien er na het publiceren nog wat gewijzigd moet worden, dan moet
    je een nieuwe versie aanmaken.
    """

    queryset = (
        BesluitType.objects.all()
        .select_related("catalogus")
        .prefetch_related("informatieobjecttypen", "zaaktypen", "resultaattype_set")
        .with_dates()
        .order_by("-pk")
    )
    serializer_class = BesluitTypeSerializer
    publish_serializer = BesluitTypePublishSerializer
    filterset_class = BesluitTypeFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
        "publish": SCOPE_CATALOGI_WRITE,
    }
    notifications_kanaal = KANAAL_BESLUITTYPEN
    concept_related_fields = ["informatieobjecttypen", "zaaktypen"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "besluittype_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "besluittype_updated",
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
                "besluittype_delete_failed",
                client_id=self.request.jwt_auth.client_id,
                uuid=uuid,
                error=str(e),
            )
            raise

        logger.info(
            "besluittype_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )

    @extend_schema(
        "besluittype_publish",
        summary="Publiceer het concept BESLUITTYPE.",
        description=(
            "Publiceren van het besluittype zorgt ervoor dat dit in een Besluiten API kan gebruikt "
            "worden. Na het publiceren van een besluittype zijn geen inhoudelijke wijzigingen "
            "meer mogelijk. Indien er na het publiceren nog wat gewijzigd moet worden, dan moet "
            "je een nieuwe versie aanmaken."
        ),
        request=None,
        responses={
            status.HTTP_200_OK: BesluitTypeSerializer,
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"], name="besluittype_publish")
    def publish(self, request, *args, **kwargs):
        response = super()._publish(request, *args, **kwargs)
        logger.info(
            "besluittype_published",
            client_id=request.jwt_auth.client_id,
            uuid=kwargs.get("uuid"),
        )
        return response
