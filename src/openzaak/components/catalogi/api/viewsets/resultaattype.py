from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import ResultaatType
from ..filters import ResultaatTypeFilter
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import ResultaatTypeSerializer
from .mixins import ZaakTypeConceptMixin


class ResultaatTypeViewSet(
    CheckQueryParamsMixin, ZaakTypeConceptMixin, viewsets.ModelViewSet
):
    """
    Opvragen en bewerken van RESULTAATTYPEn van een ZAAKTYPE.

    Het betreft de indeling of groepering van resultaten van zaken van hetzelfde
    ZAAKTYPE naar hun aard, zoals 'verleend', 'geweigerd', 'verwerkt', etc.

    create:
    Maak een RESULTAATTYPE aan.

    Maak een RESULTAATTYPE aan. Dit kan alleen als het bijbehorende ZAAKTYPE een
    concept betreft.

    list:
    Alle RESULTAATTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke RESULTAATTYPE opvragen.

    Een specifieke RESULTAATTYPE opvragen.

    update:
    Werk een RESULTAATTYPE in zijn geheel bij.

    Werk een RESULTAATTYPE in zijn geheel bij. Dit kan alleen als het
    bijbehorende ZAAKTYPE een concept betreft.

    partial_update:
    Werk een RESULTAATTYPE deels bij.

    Werk een RESULTAATTYPE deels bij. Dit kan alleen als het bijbehorende
    ZAAKTYPE een concept betreft.

    destroy:
    Verwijder een RESULTAATTYPE.

    Verwijder een RESULTAATTYPE. Dit kan alleen als het bijbehorende ZAAKTYPE
    een concept betreft.
    """

    queryset = ResultaatType.objects.all().order_by("-pk")
    serializer_class = ResultaatTypeSerializer
    filter_class = ResultaatTypeFilter
    lookup_field = "uuid"
    pagination_class = PageNumberPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAAKTYPES_READ,
        "retrieve": SCOPE_ZAAKTYPES_READ,
        "create": SCOPE_ZAAKTYPES_WRITE,
        "update": SCOPE_ZAAKTYPES_WRITE,
        "partial_update": SCOPE_ZAAKTYPES_WRITE,
        "destroy": SCOPE_ZAAKTYPES_WRITE,
    }
