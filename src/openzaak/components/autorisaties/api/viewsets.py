# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.db.models import Prefetch, Q

from drf_spectacular.utils import extend_schema, extend_schema_view
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
    ZaakType,
)
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.schema import COMMON_ERROR_RESPONSES

from ..models import CatalogusAutorisatie
from .filters import ApplicatieFilter, ApplicatieRetrieveFilter
from .kanalen import KANAAL_AUTORISATIES
from .permissions import AutorisatiesAuthRequired
from .scopes import SCOPE_AUTORISATIES_BIJWERKEN, SCOPE_AUTORISATIES_LEZEN
from .serializers import ApplicatieSerializer

logger = logging.getLogger(__name__)

IS_SUPERUSER = Q(heeft_alle_autorisaties=True)
HAS_AUTORISATIES = Q(autorisaties__isnull=False)
HAS_CATALOGUS_AUTORISATIES = Q(catalogusautorisatie__isnull=False)


@extend_schema_view(
    list=extend_schema(
        summary="Geef een collectie van applicaties, met ingesloten autorisaties.",
        description=(
            "De autorisaties zijn gedefinieerd op een specifieke component, bijvoorbeeld "
            "het ZRC, en geven aan welke scopes van toepassing zijn voor dit component. "
            "De waarde van de `component` bepaalt ook welke verdere informatie ingesloten "
            "is, zoals `zaaktype` en `maxVertrouwelijkheidaanduiding` voor het ZRC.\n"
            "\n"
            "In dit voorbeeld gelden er dus zaaktype-specifieke scopes en mogen zaken "
            "van het betreffende zaaktype met een striktere vertrouwelijkheidaanduiding "
            "dan `maxVertrouwelijkheidaanduiding` niet ontsloten worden.\n"
            "\n"
            "De collectie kan doorzocht worden met de ``clientIds`` query parameter."
        ),
    ),
    retrieve=extend_schema(
        summary="Vraag een applicatie op, met ingesloten autorisaties.",
        description=(
            "De autorisaties zijn gedefinieerd op een specifieke component, bijvoorbeeld "
            "het ZRC, en geven aan welke scopes van toepassing zijn voor dit component. "
            "De waarde van de `component` bepaalt ook welke verdere informatie ingesloten "
            "is, zoals `zaaktype` en `maxVertrouwelijkheidaanduiding` voor het ZRC.\n"
            "\n"
            "In dit voorbeeld gelden er dus zaaktype-specifieke scopes en mogen zaken "
            "van het betreffende zaaktype met een striktere vertrouwelijkheidaanduiding "
            "dan `maxVertrouwelijkheidaanduiding` niet ontsloten worden."
        ),
    ),
    create=extend_schema(
        summary="Registreer een applicatie met een bepaalde set van autorisaties.",
        description=(
            "Indien `heeftAlleAutorisaties` gezet is, dan moet je "
            "`autorisaties` leeg (of weg) laten.\n"
            "\n"
            "Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de "
            "waarde `false` hebben of weggelaten worden.\n"
            "\n"
            "Na het aanmaken wordt een notificatie verstuurd."
        ),
    ),
    update=extend_schema(
        summary="Werk de applicatie bij.",
        description=(
            "Indien `heeftAlleAutorisaties` gezet is, dan moet je "
            "`autorisaties` leeg (of weg) laten.\n"
            "\n"
            "Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de "
            "waarde `false` hebben of weggelaten worden.\n"
            "\n"
            "Na het bijwerken wordt een notificatie verstuurd."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk (een deel van) de applicatie bij.",
        description=(
            "Indien `autorisaties` meegegeven is, dan worden de bestaande `autorisaties` "
            "vervangen met de nieuwe set van `autorisaties`.\n"
            "\n"
            "Indien `heeftAlleAutorisaties` gezet is, dan moet je "
            "`autorisaties` leeg (of weg) laten.\n"
            "\n"
            "Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de "
            "waarde `false` hebben of weggelaten worden.\n"
            "\n"
            "Na het bijwerken wordt een notificatie verstuurd."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een applicatie met de bijhorende autorisaties.",
        description="Na het verwijderen wordt een notificatie verstuurd.",
    ),
)
class ApplicatieViewSet(
    CheckQueryParamsMixin, NotificationViewSetMixin, viewsets.ModelViewSet
):
    """
    Uitlezen en configureren van autorisaties voor applicaties.
    """

    queryset = (
        Applicatie.objects.exclude(
            ~IS_SUPERUSER & ~HAS_AUTORISATIES & ~HAS_CATALOGUS_AUTORISATIES
        )
        .exclude(IS_SUPERUSER & (HAS_AUTORISATIES | HAS_CATALOGUS_AUTORISATIES))
        .prefetch_related(
            "autorisaties",
            Prefetch(
                "catalogusautorisatie_set",
                queryset=CatalogusAutorisatie.objects.select_related("catalogus")
                .order_by("component")
                .prefetch_related(
                    Prefetch(
                        "catalogus__zaaktype_set",
                        queryset=ZaakType.objects.order_by("-pk"),
                    ),
                    Prefetch(
                        "catalogus__informatieobjecttype_set",
                        queryset=InformatieObjectType.objects.order_by("-pk"),
                    ),
                    Prefetch(
                        "catalogus__besluittype_set",
                        queryset=BesluitType.objects.order_by("-pk"),
                    ),
                ),
            ),
        )
        .order_by("-pk")
    )
    serializer_class = ApplicatieSerializer
    _filterset_class = ApplicatieFilter
    pagination_class = OptimizedPagination
    lookup_field = "uuid"
    permission_classes = (AutorisatiesAuthRequired,)
    required_scopes = {
        "list": SCOPE_AUTORISATIES_LEZEN,
        "retrieve": SCOPE_AUTORISATIES_LEZEN,
        "consumer": SCOPE_AUTORISATIES_LEZEN,
        "create": SCOPE_AUTORISATIES_BIJWERKEN,
        "destroy": SCOPE_AUTORISATIES_BIJWERKEN,
        "update": SCOPE_AUTORISATIES_BIJWERKEN,
        "partial_update": SCOPE_AUTORISATIES_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_AUTORISATIES

    @property
    def filterset_class(self):
        if self.action == "consumer":
            return ApplicatieRetrieveFilter
        return self._filterset_class

    def get_object(self):
        if self.action != "consumer":
            return super().get_object()

        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    @property
    def paginator(self):
        if self.action == "consumer":
            return None
        return super().paginator

    @extend_schema(
        "applicatie_consumer",
        summary="Vraag een applicatie op, op basis van clientId",
        description=(
            "Gegeven een `clientId`, via de query string, zoek de bijbehorende applicatie "
            "op. Het antwoord bevat de applicatie met ingesloten autorisaties."
        ),
        responses={
            status.HTTP_200_OK: ApplicatieSerializer(many=True),
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(methods=("get",), detail=False, name="applicatie_consumer")
    def consumer(self, request, *args, **kwargs):
        """
        Vraag een applicatie op, op basis van clientId

        Gegeven een `clientId`, via de query string, zoek de bijbehorende applicatie
        op. Het antwoord bevat de applicatie met ingesloten autorisaties.
        """
        return self.retrieve(request, *args, **kwargs)
