# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from drf_yasg.utils import no_body, swagger_auto_schema
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.settings import api_settings
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import COMMON_ERROR_RESPONSES, use_ref

from ...models import ZaakType
from ..filters import ZaakTypeFilter
from ..kanalen import KANAAL_ZAAKTYPEN
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ZaakTypeSerializer
from .mixins import (
    ConceptDestroyMixin,
    ConceptFilterMixin,
    ConceptPublishMixin,
    M2MConceptDestroyMixin,
)


@conditional_retrieve()
class ZaakTypeViewSet(
    CheckQueryParamsMixin,
    ConceptPublishMixin,
    ConceptDestroyMixin,
    ConceptFilterMixin,
    M2MConceptDestroyMixin,
    NotificationViewSetMixin,
    viewsets.ModelViewSet,
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
    - `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE.

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

    Er wordt gevalideerd op:
    - `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE.

    partial_update:
    Werk een ZAAKTYPE deels bij.

    Werk een ZAAKTYPE deels bij. Dit kan alleen als het een concept betreft.

    Er wordt gevalideerd op:
    - `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE.

    destroy:
    Verwijder een ZAAKTYPE.

    Verwijder een ZAAKTYPE. Dit kan alleen als het een concept betreft.
    """

    queryset = ZaakType.objects.prefetch_related(
        # prefetch catalogus rather than select related -> far fewer catalogi, so less data to transfer
        "catalogus",
        "statustypen",
        "zaaktypenrelaties",
        "informatieobjecttypen",
        "resultaattypen",
        "eigenschap_set",
        "roltype_set",
        "deelzaaktypen",
        "besluittypen",
    ).order_by("-pk")
    serializer_class = ZaakTypeSerializer
    lookup_field = "uuid"
    filterset_class = ZaakTypeFilter
    pagination_class = OptimizedPagination
    permission_classes = (AuthRequired,)
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
        "publish": SCOPE_CATALOGI_WRITE,
    }
    notifications_kanaal = KANAAL_ZAAKTYPEN
    concept_related_fields = ["besluittypen", "informatieobjecttypen"]

    def get_queryset(self):
        qs = super().get_queryset()

        # codepath via the the `get_viewset_for_path` utilities in various libraries
        # does not always initialize a request, which causes self.action to not be set.
        # FIXME: extract that utility into a separate library to unify it
        action = getattr(self, "action", None)
        if action != "list":
            # ⚡️ drop the prefetches when only selecting a single record. If the data
            # is needed, the queries will be done during serialization and the amount
            # of queries will be the same.
            qs = qs.prefetch_related(None)
        return qs

    def perform_update(self, serializer):

        if not serializer.partial:
            serializer.instance.zaaktypenrelaties.all().delete()

        super().perform_update(serializer)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            status.HTTP_200_OK: serializer_class,
            status.HTTP_400_BAD_REQUEST: use_ref,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        """
        Publiceer het concept ZAAKTYPE.

        Publiceren van het zaaktype zorgt ervoor dat dit in een Zaken API kan gebruikt
        worden. Na het publiceren van een zaaktype zijn geen inhoudelijke wijzigingen
        meer mogelijk - ook niet de statustypen, eigenschappen... etc. Indien er na het
        publiceren nog wat gewijzigd moet worden, dan moet je een nieuwe versie
        aanmaken.
        """
        instance = self.get_object()

        # check related objects
        if (
            instance.besluittypen.filter(concept=True).exists()
            or instance.informatieobjecttypen.filter(concept=True).exists()
            or instance.deelzaaktypen.filter(concept=True).exists()
        ):
            msg = _("All related resources should be published")
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: msg}, code="concept-relation"
            )

        instance.concept = False
        instance.save()

        serializer = self.get_serializer(instance)

        return Response(serializer.data)
