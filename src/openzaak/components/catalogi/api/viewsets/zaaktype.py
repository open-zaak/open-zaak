from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import ZaakType
from ..filters import ZaakTypeFilter
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import ZaakTypeSerializer
from .mixins import M2MConceptDestroyMixin, ConceptDestroyMixin, ConceptFilterMixin
from django.utils.translation import ugettext_lazy as _

from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response


class ZaakTypeViewSet(
    CheckQueryParamsMixin, ConceptDestroyMixin, ConceptFilterMixin, M2MConceptDestroyMixin, viewsets.ModelViewSet
):
    """
    Opvragen en bewerken van ZAAKTYPEn nodig voor ZAKEN in de Zaken API.

    Een ZAAKTYPE beschrijft het geheel van karakteristieke eigenschappen van
    zaken van eenzelfde soort.

    create:
    Maak een ZAAKTYPE aan.

    Maak een ZAAKTYPE aan.

    Er wordt gevalideerd op:
    - geldigheid `catalogus` URL, dit moet een catalogus binnen dezelfde API zijn
    - Uniciteit `catalogus` en `omschrijving`. Dezelfde omeschrijving mag enkel
      opnieuw gebruikt worden als het zaaktype een andere geldigheidsperiode
      kent dan bestaande zaaktypen.

    list:
    Alle ZAAKTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ZAAKTYPE opvragen.

    Een specifieke ZAAKTYPE opvragen.

    update:
    Werk een ZAAKTYPE in zijn geheel bij.

    Werk een ZAAKTYPE in zijn geheel bij. Dit kan alleen als het een concept
    betreft.

    partial_update:
    Werk een ZAAKTYPE deels bij.

    Werk een ZAAKTYPE deels bij. Dit kan alleen als het een concept betreft.

    destroy:
    Verwijder een ZAAKTYPE.

    Verwijder een ZAAKTYPE. Dit kan alleen als het een concept betreft.
    """

    queryset = ZaakType.objects.prefetch_related(
        "statustypen",
        "zaaktypenrelaties",
        "informatieobjecttypen",
        "statustypen",
        "resultaattypen",
        "eigenschap_set",
        "roltype_set",
        "besluittypen",
    ).order_by("-pk")
    serializer_class = ZaakTypeSerializer
    lookup_field = "uuid"
    filterset_class = ZaakTypeFilter
    pagination_class = PageNumberPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAAKTYPES_READ,
        "retrieve": SCOPE_ZAAKTYPES_READ,
        "create": SCOPE_ZAAKTYPES_WRITE,
        "update": SCOPE_ZAAKTYPES_WRITE,
        "partial_update": SCOPE_ZAAKTYPES_WRITE,
        "destroy": SCOPE_ZAAKTYPES_WRITE,
        "publish": SCOPE_ZAAKTYPES_WRITE,
    }
    concept_related_fields = ["besluittypen", "informatieobjecttypen"]

    @swagger_auto_schema(request_body=no_body)
    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()

        # check related objects
        besluittypen = instance.besluittype_set.all()
        informatieobjecttypen = instance.heeft_relevant_informatieobjecttype.all()

        for types in [besluittypen, informatieobjecttypen]:
            for relative_type in types:
                if relative_type.concept:
                    msg = _("All relative resources should be published")
                    raise PermissionDenied(detail=msg)

        instance.concept = False
        instance.save()

        serializer = self.get_serializer(instance)

        return Response(serializer.data)
