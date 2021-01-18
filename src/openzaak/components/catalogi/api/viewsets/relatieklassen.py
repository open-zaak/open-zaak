# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import AutoSchema

from ...models import ZaakTypeInformatieObjectType
from ..filters import ZaakTypeInformatieObjectTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ZaakTypeInformatieObjectTypeSerializer
from .mixins import ConceptDestroyMixin, ConceptFilterMixin


class ZaakTypeInformatieObjectTypeSchema(AutoSchema):
    def get_operation_id(self, operation_keys=None):
        return f"zaakinformatieobjecttype_{operation_keys[-1]}"


class ZaakTypeInformatieObjectTypeViewSet(
    CheckQueryParamsMixin,
    ConceptFilterMixin,
    ConceptDestroyMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKTYPE-INFORMATIEOBJECTTYPE relaties.

    Geeft aan welke INFORMATIEOBJECTTYPEn binnen een ZAAKTYPE mogelijk zijn en
    hoe de richting is.

    create:
    Maak een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie aan.

    Maak een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie aan. Dit kan alleen als het
    bijbehorende ZAAKTYPE een concept betreft.

    Er wordt gevalideerd op:
    - `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`

    list:
    Alle ZAAKTYPE-INFORMATIEOBJECTTYPE relaties opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ZAAKTYPE-INFORMATIEOBJECTTYPE relatie opvragen.

    Een specifieke ZAAKTYPE-INFORMATIEOBJECTTYPE relatie opvragen.

    update:
    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie in zijn geheel bij.

    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie in zijn geheel bij. Dit kan
    alleen als het bijbehorende ZAAKTYPE een concept betreft.

    Er wordt gevalideerd op:
    - `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`

    partial_update:
    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij.

    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij. Dit kan alleen
    als het bijbehorende ZAAKTYPE een concept betreft.

    Er wordt gevalideerd op:
    - `zaaktype` en `informatieobjecttype` behoren tot dezelfde `catalogus`

    destroy:
    Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie.

    Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie. Dit kan alleen als
    het bijbehorende ZAAKTYPE een concept betreft.

    Er wordt gevalideerd op:
    - `zaaktype` of `informatieobjecttype` is nog niet gepubliceerd
    """

    queryset = (
        ZaakTypeInformatieObjectType.objects.all()
        .select_related("zaaktype", "informatieobjecttype")
        .order_by("-pk")
    )
    serializer_class = ZaakTypeInformatieObjectTypeSerializer
    filterset_class = ZaakTypeInformatieObjectTypeFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "update": SCOPE_CATALOGI_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
    }
    swagger_schema = ZaakTypeInformatieObjectTypeSchema

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
