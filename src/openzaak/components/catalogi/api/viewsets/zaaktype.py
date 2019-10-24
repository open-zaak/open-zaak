from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.permissions import AuthRequired

from ...models import ZaakType
from ..filters import ZaakTypeFilter
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import ZaakTypeSerializer
from .mixins import ConceptMixin, M2MConceptDestroyMixin


class ZaakTypeViewSet(
    CheckQueryParamsMixin, ConceptMixin, M2MConceptDestroyMixin, viewsets.ModelViewSet
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
    relation_fields = ["zaaktypenrelaties"]

    def perform_create(self, serializer):
        for field_name in self.relation_fields:
            field = serializer.validated_data.get(field_name, [])
            for related_object in field:
                # TODO fix url lookup to check if concept
                if not related_object["gerelateerd_zaaktype"]:
                    msg = _(
                        f"Relations to non-concept {field_name} object can't be created"
                    )
                    raise PermissionDenied(detail=msg)

        super().perform_create(serializer)

    def perform_update(self, instance):
        for field_name in self.relation_fields:
            field = getattr(self.get_object(), field_name)
            # TODO fix url lookup to check if concept
            related_non_concepts = field.filter(zaaktype__concept=False)
            if related_non_concepts.exists():
                msg = _(f"Objects related to non-concept {field_name} can't be updated")
                raise PermissionDenied(detail=msg)

        super().perform_update(instance)

    def perform_destroy(self, instance):
        for field_name in self.relation_fields:
            field = getattr(instance, field_name)
            # TODO fix url lookup to check if concept
            related_non_concepts = field.filter(zaaktype__concept=False)
            if related_non_concepts.exists():
                msg = _(
                    f"Objects related to non-concept {field_name} can't be destroyed"
                )
                raise PermissionDenied(detail=msg)

        super().perform_destroy(instance)
