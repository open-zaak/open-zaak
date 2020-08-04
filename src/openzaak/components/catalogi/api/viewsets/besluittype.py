# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.notifications.viewsets import NotificationViewSetMixin
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import BesluitType
from ..filters import BesluitTypeFilter
from ..kanalen import KANAAL_BESLUITTYPEN
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import BesluitTypeSerializer
from .mixins import ConceptMixin, M2MConceptDestroyMixin


class BesluitTypeViewSet(
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

    create:
    Maak een BESLUITTYPE aan.

    Maak een BESLUITTYPE aan.

    list:
    Alle BESLUITTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke BESLUITTYPE opvragen.

    Een specifieke BESLUITTYPE opvragen.

    update:
    Werk een BESLUITTYPE in zijn geheel bij.

    Werk een BESLUITTYPE in zijn geheel bij. Dit kan alleen als het een concept
    betreft.

    partial_update:
    Werk een BESLUITTYPE deels bij.

    Werk een BESLUITTYPE deels bij. Dit kan alleen als het een concept betreft.

    destroy:
    Verwijder een BESLUITTYPE.

    Verwijder een BESLUITTYPE. Dit kan alleen als het een concept betreft.
    """

    queryset = (
        BesluitType.objects.all()
        .select_related("catalogus")
        .prefetch_related("informatieobjecttypen", "zaaktypen")
        .order_by("-pk")
    )
    serializer_class = BesluitTypeSerializer
    filterset_class = BesluitTypeFilter
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
        "publish": SCOPE_CATALOGI_WRITE,
    }
    notifications_kanaal = KANAAL_BESLUITTYPEN
    concept_related_fields = ["informatieobjecttypen", "zaaktypen"]
