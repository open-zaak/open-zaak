# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from vng_api_common.caching import conditional_retrieve
from vng_api_common.utils import get_help_text
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.help_text import mark_experimental
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import COMMON_ERROR_RESPONSES, VALIDATION_ERROR_RESPONSES

from ...models import InformatieObjectType
from ..filters import InformatieObjectTypeFilter
from ..kanalen import KANAAL_INFORMATIEOBJECTTYPEN
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import (
    InformatieObjectTypePublishSerializer,
    InformatieObjectTypeSerializer,
)
from .mixins import ConceptMixin, M2MConceptDestroyMixin


@extend_schema_view(
    list=extend_schema(
        summary="Alle INFORMATIEOBJECTTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
        parameters=[
            OpenApiParameter(
                name="zaaktype",
                type=OpenApiTypes.URI,
                location=OpenApiParameter.QUERY,
                description=mark_experimental(
                    get_help_text("catalogi.ZaakTypeInformatieObjectType", "zaaktype")
                ),
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Een specifieke INFORMATIEOBJECTTYPE opvragen.",
        description="Een specifieke INFORMATIEOBJECTTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een INFORMATIEOBJECTTYPE aan.",
        description="Maak een INFORMATIEOBJECTTYPE aan.",
    ),
    update=extend_schema(
        summary="Werk een INFORMATIEOBJECTTYPE in zijn geheel bij.",
        description=(
            "Werk een INFORMATIEOBJECTTYPE in zijn geheel bij. Dit kan alleen als het een "
            "concept betreft."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een INFORMATIEOBJECTTYPE deels bij.",
        description=(
            "Werk een INFORMATIEOBJECTTYPE deels bij. Dit kan alleen als het een concept "
            "betreft."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een INFORMATIEOBJECTTYPE.",
        description=(
            "Verwijder een INFORMATIEOBJECTTYPE. Dit kan alleen als het een concept "
            "betreft."
        ),
    ),
)
@conditional_retrieve()
class InformatieObjectTypeViewSet(
    CheckQueryParamsMixin,
    ConceptMixin,
    M2MConceptDestroyMixin,
    NotificationViewSetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van INFORMATIEOBJECTTYPEn nodig voor
    INFORMATIEOBJECTen in de Documenten API.

    Een INFORMATIEOBJECTTYPE beschijft de karakteristieken van een document of
    ander object dat informatie bevat.

    publish:
    Publiceer het concept INFORMATIEOBJECTTYPE.

    Publiceren van het informatieobjecttype zorgt ervoor dat dit in een Documenten API
    kan gebruikt worden. Na het publiceren van een informatieobjecttype zijn geen
    inhoudelijke wijzigingen meer mogelijk. Indien er na het publiceren nog wat
    gewijzigd moet worden, dan moet je een nieuwe versie aanmaken.
    """

    queryset = (
        InformatieObjectType.objects.all()
        .select_related("catalogus")
        .with_dates()
        .order_by("-pk")
    )
    serializer_class = InformatieObjectTypeSerializer
    publish_serializer = InformatieObjectTypePublishSerializer
    filterset_class = InformatieObjectTypeFilter
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
    notifications_kanaal = KANAAL_INFORMATIEOBJECTTYPEN
    concept_related_fields = ["besluittypen", "zaaktypen"]

    @extend_schema(
        "informatieobjecttype_publish",
        summary="Publiceer het concept INFORMATIEOBJECTTYPE.",
        description=(
            "Publiceren van het informatieobjecttype zorgt ervoor dat dit in een Documenten API "
            "kan gebruikt worden. Na het publiceren van een informatieobjecttype zijn geen "
            "inhoudelijke wijzigingen meer mogelijk. Indien er na het publiceren nog wat "
            "gewijzigd moet worden, dan moet je een nieuwe versie aanmaken."
        ),
        request=None,
        responses={
            status.HTTP_200_OK: InformatieObjectTypeSerializer,
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"], name="informatieobjecttype_publish")
    def publish(self, *args, **kwargs):
        return super()._publish(*args, **kwargs)
