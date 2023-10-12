# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired

from ...models import ZaakObjectType
from ..filters import ZaakObjectTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ZaakObjectTypeSerializer
from .mixins import ZaakTypeConceptMixin


@conditional_retrieve()
class ZaakObjectTypeViewSet(
    CheckQueryParamsMixin, ZaakTypeConceptMixin, viewsets.ModelViewSet
):
    """
    Opvragen en bewerken van ZAAKOBJECTTYPEn.

    create:
    Maak een ZAAKOBJECTTYPE aan.

    Maak een ZAAKOBJECTTYPE aan.

    list:
    Alle ZAAKOBJECTTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ZAAKOBJECTTYPE opvragen.

    Een specifieke ZAAKOBJECTTYPE opvragen.

    update:
    Werk een ZAAKOBJECTTYPE in zijn geheel bij.

    Werk een ZAAKOBJECTTYPE in zijn geheel bij.

    partial_update:
    Werk een ZAAKOBJECTTYPE deels bij.

    Werk een ZAAKOBJECTTYPE deels bij.

    destroy:
    Verwijder een ZAAKOBJECTTYPE.

    Verwijder een ZAAKOBJECTTYPE.
    """

    queryset = (
        ZaakObjectType.objects.select_related(
            "zaaktype", "zaaktype__catalogus", "statustype"
        )
        .prefetch_related("resultaattypen")
        .order_by("-pk")
        .all()
    )
    serializer_class = ZaakObjectTypeSerializer
    filterset_class = ZaakObjectTypeFilter
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
