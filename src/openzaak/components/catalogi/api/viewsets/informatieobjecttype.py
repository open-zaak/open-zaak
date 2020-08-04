# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.notifications.viewsets import NotificationViewSetMixin
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import InformatieObjectType
from ..filters import InformatieObjectTypeFilter
from ..kanalen import KANAAL_INFORMATIEOBJECTTYPEN
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import InformatieObjectTypeSerializer
from .mixins import ConceptMixin, M2MConceptDestroyMixin


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

    create:
    Maak een INFORMATIEOBJECTTYPE aan.

    Maak een INFORMATIEOBJECTTYPE aan.

    list:
    Alle INFORMATIEOBJECTTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke INFORMATIEOBJECTTYPE opvragen.

    Een specifieke INFORMATIEOBJECTTYPE opvragen.

    update:
    Werk een INFORMATIEOBJECTTYPE in zijn geheel bij.

    Werk een INFORMATIEOBJECTTYPE in zijn geheel bij. Dit kan alleen als het een
    concept betreft.

    partial_update:
    Werk een INFORMATIEOBJECTTYPE deels bij.

    Werk een INFORMATIEOBJECTTYPE deels bij. Dit kan alleen als het een concept
    betreft.

    destroy:
    Verwijder een INFORMATIEOBJECTTYPE.

    Verwijder een INFORMATIEOBJECTTYPE. Dit kan alleen als het een concept
    betreft.
    """

    queryset = (
        InformatieObjectType.objects.all().select_related("catalogus").order_by("-pk")
    )
    serializer_class = InformatieObjectTypeSerializer
    filterset_class = InformatieObjectTypeFilter
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
    notifications_kanaal = KANAAL_INFORMATIEOBJECTTYPEN
    concept_related_fields = ["besluittypen", "zaaktypen"]
