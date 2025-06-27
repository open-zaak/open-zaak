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

from ...models import ResultaatType
from ..filters import ResultaatTypeFilter
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
    ZaakTypeConceptMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van RESULTAATTYPEn van een ZAAKTYPE.

    Het betreft de indeling of groepering van resultaten van zaken van hetzelfde
    ZAAKTYPE naar hun aard, zoals 'verleend', 'geweigerd', 'verwerkt', etc.
    """

    queryset = (
        ResultaatType.objects.all()
        .select_related("zaaktype", "zaaktype__catalogus")
        .prefetch_related("besluittypen", "informatieobjecttypen")
        .order_by("-pk")
    )
    serializer_class = ResultaatTypeSerializer
    filterset_class = ResultaatTypeFilter
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

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        logger.info(
            "resultaattype_list_completed",
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
            "resultaattype_retrieve_completed",
            user=str(request.user),
            uuid=kwargs.get("uuid"),
            view=self.__class__.__name__,
        )
        return response

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(
            "resultaattype_create_completed",
            user=str(request.user),
            created_id=response.data.get("uuid"),
            view=self.__class__.__name__,
        )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(
            "resultaattype_update_completed",
            user=str(request.user),
            uuid=kwargs.get("uuid"),
            view=self.__class__.__name__,
        )
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        logger.info(
            "resultaattype_partial_update_completed",
            user=str(request.user),
            uuid=kwargs.get("uuid"),
            view=self.__class__.__name__,
        )
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(
            "resultaattype_destroy_completed",
            user=str(request.user),
            uuid=kwargs.get("uuid"),
            view=self.__class__.__name__,
        )
        return response
