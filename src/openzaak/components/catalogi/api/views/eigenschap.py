from openzaak.components.catalogi.models import Eigenschap
from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination

from ..filters import EigenschapFilter
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import EigenschapSerializer
from .mixins import ZaakTypeConceptMixin


class EigenschapViewSet(ZaakTypeConceptMixin,
                        mixins.CreateModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.ReadOnlyModelViewSet):
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
    queryset = Eigenschap.objects.all().order_by('-pk')
    serializer_class = EigenschapSerializer
    filterset_class = EigenschapFilter
    lookup_field = 'uuid'
    pagination_class = PageNumberPagination
    required_scopes = {
        'list': SCOPE_ZAAKTYPES_READ,
        'retrieve': SCOPE_ZAAKTYPES_READ,
        'create': SCOPE_ZAAKTYPES_WRITE,
        'destroy': SCOPE_ZAAKTYPES_WRITE,
    }
