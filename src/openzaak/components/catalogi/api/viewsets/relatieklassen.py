# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import ZaakTypeInformatieObjectType
from ..filters import ZaakTypeInformatieObjectTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ZaakTypeInformatieObjectTypeSerializer
from .mixins import ConceptDestroyMixin, ConceptFilterMixin


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKTYPE-INFORMATIEOBJECTTYPE relaties opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAKTYPE-INFORMATIEOBJECTTYPE relatie opvragen.",
        description="Een specifieke ZAAKTYPE-INFORMATIEOBJECTTYPE relatie opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie aan.",
        description=(
            "Maak een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie aan. Dit kan alleen als het "
            "bijbehorende ZAAKTYPE een concept betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`"
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie in zijn geheel bij.",
        description=(
            "Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie in zijn geheel bij. Dit kan "
            "alleen als het bijbehorende ZAAKTYPE een concept betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`"
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij.",
        description=(
            "Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij. Dit kan alleen "
            "als het bijbehorende ZAAKTYPE een concept betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie.",
        description=(
            "Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie. Dit kan alleen als "
            "het bijbehorende ZAAKTYPE een concept betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `zaaktype` of `informatieobjecttype` is nog niet gepubliceerd"
        ),
    ),
)
@conditional_retrieve()
class ZaakTypeInformatieObjectTypeViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ConceptFilterMixin,
    ConceptDestroyMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKTYPE-INFORMATIEOBJECTTYPE relaties.

    Geeft aan welke INFORMATIEOBJECTTYPEn binnen een ZAAKTYPE mogelijk zijn en
    hoe de richting is.
    """

    queryset = (
        ZaakTypeInformatieObjectType.objects.all()
        .select_related("zaaktype", "informatieobjecttype", "zaaktype__catalogus")
        .order_by("-pk")
    )
    serializer_class = ZaakTypeInformatieObjectTypeSerializer
    filterset_class = ZaakTypeInformatieObjectTypeFilter
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

    def get_concept(self, instance):
        ziot = self.get_object()
        zaaktype = getattr(instance, "zaaktype", None) or ziot.zaaktype
        informatieobjecttype = (
            getattr(instance, "informatieobjecttype", None) or ziot.informatieobjecttype
        )
        return zaaktype.concept or informatieobjecttype.concept

    def get_concept_filter(self):
        return ~(Q(zaaktype__concept=True) | Q(informatieobjecttype__concept=True))

    def perform_destroy(self, instance):
        forced_delete = self.request.jwt_auth.has_auth(
            scopes=SCOPE_CATALOGI_FORCED_DELETE,
            init_component=self.queryset.model._meta.app_label,
        )

        if not forced_delete:
            if not self.get_concept(instance):
                msg = _("Objects related to non-concept objects can't be destroyed")
                raise ValidationError(
                    {"nonFieldErrors": msg}, code="non-concept-relation"
                )

        super().perform_destroy(instance)
