from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import ZaakInformatieobjectType
from ..filters import ZaakInformatieobjectTypeFilter
from ..scopes import (
    SCOPE_ZAAKTYPES_FORCED_DELETE,
    SCOPE_ZAAKTYPES_READ,
    SCOPE_ZAAKTYPES_WRITE,
)
from ..serializers import ZaakTypeInformatieObjectTypeSerializer
from .mixins import ConceptDestroyMixin, ConceptFilterMixin


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

    partial_update:
    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij.

    Werk een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie deels bij. Dit kan alleen
    als het bijbehorende ZAAKTYPE een concept betreft.

    destroy:
    Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie.

    Verwijder een ZAAKTYPE-INFORMATIEOBJECTTYPE relatie. Dit kan alleen als
    het bijbehorende ZAAKTYPE een concept betreft.
    """

    queryset = (
        ZaakInformatieobjectType.objects.all()
        .select_related("zaaktype", "informatieobjecttype")
        .order_by("-pk")
    )
    serializer_class = ZaakTypeInformatieObjectTypeSerializer
    filterset_class = ZaakInformatieobjectTypeFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAAKTYPES_READ,
        "retrieve": SCOPE_ZAAKTYPES_READ,
        "create": SCOPE_ZAAKTYPES_WRITE,
        "update": SCOPE_ZAAKTYPES_WRITE,
        "partial_update": SCOPE_ZAAKTYPES_WRITE,
        "destroy": SCOPE_ZAAKTYPES_WRITE | SCOPE_ZAAKTYPES_FORCED_DELETE,
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
            scopes=SCOPE_ZAAKTYPES_FORCED_DELETE,
            init_component=self.queryset.model._meta.app_label,
        )

        if not forced_delete:
            if not self.get_concept(instance):
                msg = _("Objects related to non-concept objects can't be destroyed")
                raise ValidationError(
                    {"nonFieldErrors": msg}, code="non-concept-relation"
                )

        super().perform_destroy(instance)
