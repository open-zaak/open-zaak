from openzaak.components.catalogi.models import Catalogus
from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination

from ..filters import CatalogusFilter
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import CatalogusSerializer


class CatalogusViewSet(mixins.CreateModelMixin,
                       viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en bewerken van CATALOGUSsen.

    De verzameling van ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn voor
    een domein die als één geheel beheerd wordt.

    create:
    Maak een CATALOGUS aan.

    Maak een CATALOGUS aan.

    list:
    Alle CATALOGUSsen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke CATALOGUS opvragen.

    Een specifieke CATALOGUS opvragen.

    update:
    Werk een CATALOGUS in zijn geheel bij.

    Werk een CATALOGUS in zijn geheel bij.

    partial_update:
    Werk een CATALOGUS deels bij.

    Werk een CATALOGUS deels bij.

    destroy:
    Verwijder een CATALOGUS.

    Verwijder een CATALOGUS. Dit kan alleen als er geen onderliggende
    ZAAKTYPEn, INFORMATIEOBJECTTYPEn en BESLUITTYPEn zijn.
    """
    queryset = Catalogus.objects.all().order_by('-pk')
    serializer_class = CatalogusSerializer
    filter_class = CatalogusFilter
    lookup_field = 'uuid'
    pagination_class = PageNumberPagination
    required_scopes = {
        'list': SCOPE_ZAAKTYPES_READ,
        'retrieve': SCOPE_ZAAKTYPES_READ,
        'create': SCOPE_ZAAKTYPES_WRITE,
        'destroy': SCOPE_ZAAKTYPES_WRITE,
    }
