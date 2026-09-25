# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db.models import Prefetch

import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin, ExpandMixin
from openzaak.utils.pagination import ExactPagination
from openzaak.utils.permissions import AuthRequired

from ...models import (
    BesluitType,
    InformatieObjectType,
    ResultaatType,
)
from ..filters import ResultaatTypeDetailFilter, ResultaatTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ResultaatTypeSerializer
from .mixins import ZaakTypeConceptMixin

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle RESULTAATTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke RESULTAATTYPE opvragen.",
        description="Een specifieke RESULTAATTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een RESULTAATTYPE aan.",
        description=(
            "Maak een RESULTAATTYPE aan. Dit kan alleen als het bijbehorende ZAAKTYPE een "
            "concept betreft."
        ),
    ),
    update=extend_schema(
        summary="Werk een RESULTAATTYPE in zijn geheel bij.",
        description=(
            "Werk een RESULTAATTYPE in zijn geheel bij. Dit kan alleen als het "
            "bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een RESULTAATTYPE deels bij.",
        description=(
            "Werk een RESULTAATTYPE deels bij. Dit kan alleen als het bijbehorende "
            "ZAAKTYPE een concept betreft."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een RESULTAATTYPE.",
        description=(
            "Verwijder een RESULTAATTYPE. Dit kan alleen als het bijbehorende ZAAKTYPE "
            "een concept betreft."
        ),
    ),
)
@conditional_retrieve()
class ResultaatTypeViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ExpandMixin,
    ZaakTypeConceptMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van RESULTAATTYPEn van een ZAAKTYPE.

    Het betreft de indeling of groepering van resultaten van zaken van hetzelfde
    ZAAKTYPE naar hun aard, zoals 'verleend', 'geweigerd', 'verwerkt', etc.
    """

    queryset = ResultaatType.objects.select_related(
        "zaaktype",
        "zaaktype__catalogus",
    ).order_by("-pk")

    def get_queryset(self):
        qs = super().get_queryset()

        request = getattr(self, "request", None)

        if request is not None and hasattr(request, "data"):
            inclusions = self.get_requested_inclusions(request)
        else:
            inclusions = None

        # Prefetch the expanded resource only when inclusions are requested.
        if inclusions:
            qs = qs.prefetch_related(
                Prefetch(
                    "besluittypen",
                    queryset=BesluitType.objects.select_related(
                        "catalogus"
                    ).prefetch_related(
                        "resultaattype_set",
                        "informatieobjecttypen",
                        "zaaktypen",
                    ),
                ),
                Prefetch(
                    "informatieobjecttypen",
                    queryset=InformatieObjectType.objects.select_related(
                        "catalogus"
                    ).prefetch_related(
                        "zaaktypen",
                        "besluittypen",
                    ),
                ),
                "zaaktype__informatieobjecttypen",
                "zaaktype__statustypen",
                "zaaktype__resultaattypen",
                "zaaktype__eigenschap_set",
                "zaaktype__roltype_set",
                "zaaktype__besluittypen",
                "zaaktype__zaakobjecttype_set",
                "zaaktype__zaaktypenrelaties",
                "zaaktype__deelzaaktypen",
            )
        else:
            qs = qs.prefetch_related(
                "besluittypen",
                "informatieobjecttypen",
                "zaaktype__informatieobjecttypen",
            )

        return qs

    serializer_class = ResultaatTypeSerializer
    lookup_field = "uuid"
    pagination_class = ExactPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
    }

    @property
    def filterset_class(self):
        """
        support expand in the detail endpoint
        """
        if self.detail:
            return ResultaatTypeDetailFilter
        return ResultaatTypeFilter

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "resultaattype_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "resultaattype_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        super().perform_destroy(instance)
        logger.info(
            "resultaattype_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )
