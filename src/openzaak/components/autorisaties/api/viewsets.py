# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.notifications.viewsets import NotificationViewSetMixin
from vng_api_common.viewsets import CheckQueryParamsMixin

from ._schema_overrides import ApplicatieConsumerAutoSchema
from .filters import ApplicatieFilter, ApplicatieRetrieveFilter
from .kanalen import KANAAL_AUTORISATIES
from .permissions import AutorisatiesAuthRequired
from .scopes import SCOPE_AUTORISATIES_BIJWERKEN, SCOPE_AUTORISATIES_LEZEN
from .serializers import ApplicatieSerializer

logger = logging.getLogger(__name__)


class ApplicatieViewSet(
    CheckQueryParamsMixin, NotificationViewSetMixin, viewsets.ModelViewSet
):
    """
    Uitlezen en configureren van autorisaties voor applicaties.

    list:
    Geef een collectie van applicaties, met ingesloten autorisaties.

    De autorisaties zijn gedefinieerd op een specifieke component, bijvoorbeeld
    het ZRC, en geven aan welke scopes van toepassing zijn voor dit component.
    De waarde van de `component` bepaalt ook welke verdere informatie ingesloten
    is, zoals `zaaktype` en `maxVertrouwelijkheidaanduiding` voor het ZRC.

    In dit voorbeeld gelden er dus zaaktype-specifieke scopes en mogen zaken
    van het betreffende zaaktype met een striktere vertrouwelijkheidaanduiding
    dan `maxVertrouwelijkheidaanduiding` niet ontsloten worden.

    De collectie kan doorzocht worden met de ``clientIds`` query parameter.

    retrieve:
    Vraag een applicatie op, met ingesloten autorisaties.

    De autorisaties zijn gedefinieerd op een specifieke component, bijvoorbeeld
    het ZRC, en geven aan welke scopes van toepassing zijn voor dit component.
    De waarde van de `component` bepaalt ook welke verdere informatie ingesloten
    is, zoals `zaaktype` en `maxVertrouwelijkheidaanduiding` voor het ZRC.

    In dit voorbeeld gelden er dus zaaktype-specifieke scopes en mogen zaken
    van het betreffende zaaktype met een striktere vertrouwelijkheidaanduiding
    dan `maxVertrouwelijkheidaanduiding` niet ontsloten worden.

    create:
    Registreer een applicatie met een bepaalde set van autorisaties.

    Indien `heeftAlleAutorisaties` gezet is, dan moet je
    `autorisaties` leeg (of weg) laten.

    Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de
    waarde `false` hebben of weggelaten worden.

    Na het aanmaken wordt een notificatie verstuurd.

    update:
    Werk de applicatie bij.

    Indien `heeftAlleAutorisaties` gezet is, dan moet je
    `autorisaties` leeg (of weg) laten.

    Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de
    waarde `false` hebben of weggelaten worden.

    Na het bijwerken wordt een notificatie verstuurd.

    partial_update:
    Werk (een deel van) de applicatie bij.

    Indien `autorisaties` meegegeven is, dan worden de bestaande `autorisaties`
    vervangen met de nieuwe set van `autorisaties`.

    Indien `heeftAlleAutorisaties` gezet is, dan moet je
    `autorisaties` leeg (of weg) laten.

    Indien je `autorisaties` meegeeft, dan moet `heeftAlleAutorisaties` de
    waarde `false` hebben of weggelaten worden.

    Na het bijwerken wordt een notificatie verstuurd.

    destroy:
    Verwijder een applicatie met de bijhorende autorisaties.

    Na het verwijderen wordt een notificatie verstuurd.
    """

    queryset = Applicatie.objects.prefetch_related("autorisaties").order_by("-pk")
    serializer_class = ApplicatieSerializer
    _filterset_class = ApplicatieFilter
    pagination_class = PageNumberPagination
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

    @swagger_auto_schema(auto_schema=ApplicatieConsumerAutoSchema)
    @action(methods=("get",), detail=False)
    def consumer(self, request, *args, **kwargs):
        """
        Vraag een applicatie op, op basis van clientId

        Gegeven een `clientId`, via de query string, zoek de bijbehorende applicatie
        op. Het antwoord bevat de applicatie met ingesloten autorisaties.
        """
        return self.retrieve(request, *args, **kwargs)
