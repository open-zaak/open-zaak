# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db.models import Prefetch

import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin, ExpandMixin
from openzaak.utils.pagination import ExactPagination
from openzaak.utils.permissions import AuthRequired

from ...models import BesluitType, Catalogus, InformatieObjectType, ZaakType
from ..filters import CatalogusDetailFilter, CatalogusFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
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
    update=extend_schema(
        summary="Werk een CATALOGUS in zijn geheel bij.",
        description=("Werk een CATALOGUS in zijn geheel bij."),
    ),
    partial_update=extend_schema(
        summary="Werk een CATALOGUS deels bij.",
        description="Werk een CATALOGUS deels bij.",
    ),
)
@conditional_retrieve()
class CatalogusViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ExpandMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van CATALOGUSsen.
    """

    queryset = (
        Catalogus.objects.all()
        .prefetch_related(
            Prefetch(
                "zaaktype_set",
                queryset=(
                    ZaakType.objects.select_related("catalogus").prefetch_related(
                        "informatieobjecttypen",
                        "statustypen",
                        "resultaattypen",
                        "eigenschap_set",
                        "roltype_set",
                        "besluittypen",
                        "zaakobjecttype_set",
                        "zaaktypenrelaties",
                        "deelzaaktypen",
                    )
                ),
            ),
            Prefetch(
                "besluittype_set",
                queryset=(
                    BesluitType.objects.select_related("catalogus").prefetch_related(
                        "resultaattype_set",
                        "zaaktypen",
                        "informatieobjecttypen",
                    )
                ),
            ),
            Prefetch(
                "informatieobjecttype_set",
                queryset=(
                    InformatieObjectType.objects.select_related(
                        "catalogus"
                    ).prefetch_related(
                        "zaaktypen",
                        "besluittypen",
                    )
                ),
            ),
        )
        .order_by("-pk")
    )
    serializer_class = CatalogusSerializer
    lookup_field = "uuid"
    pagination_class = ExactPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
    }

    @property
    def filterset_class(self):
        """
        support expand in the detail endpoint
        """
        if self.detail:
            return CatalogusDetailFilter
        return CatalogusFilter

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "catalogus_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "catalogus_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )
