# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.components.catalogi.models import Eigenschap
from openzaak.utils.permissions import AuthRequired

from ..filters import EigenschapFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import EigenschapSerializer
from .mixins import ZaakTypeConceptMixin


class EigenschapViewSet(
    CheckQueryParamsMixin, ZaakTypeConceptMixin, viewsets.ModelViewSet
):
    """
    Opvragen en bewerken van EIGENSCHAPpen van een ZAAKTYPE.

    Een relevant inhoudelijk gegeven dat bij ZAAKen van dit ZAAKTYPE
    geregistreerd moet kunnen worden en geen standaard kenmerk is van een zaak.

    create:
    Maak een EIGENSCHAP aan.

    Maak een EIGENSCHAP aan. Dit kan alleen als het bijbehorende ZAAKTYPE een
    concept betreft.

    list:
    Alle EIGENSCHAPpen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke EIGENSCHAP opvragen.

    Een specifieke EIGENSCHAP opvragen.

    update:
    Werk een EIGENSCHAP in zijn geheel bij.

    Werk een EIGENSCHAP in zijn geheel bij. Dit kan alleen als het
    bijbehorende ZAAKTYPE een concept betreft.

    partial_update:
    Werk een EIGENSCHAP deels bij.

    Werk een EIGENSCHAP deels bij. Dit kan alleen als het bijbehorende
    ZAAKTYPE een concept betreft.

    destroy:
    Verwijder een EIGENSCHAP.

    Verwijder een EIGENSCHAP. Dit kan alleen als het bijbehorende ZAAKTYPE een
    concept betreft.
    """

    queryset = (
        Eigenschap.objects.all()
        .select_related("specificatie_van_eigenschap", "zaaktype")
        .order_by("-pk")
    )
    serializer_class = EigenschapSerializer
    filterset_class = EigenschapFilter
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
