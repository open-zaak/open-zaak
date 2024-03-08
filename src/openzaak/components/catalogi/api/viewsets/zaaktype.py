# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.serializers import ValidationError
from rest_framework.settings import api_settings
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import COMMON_ERROR_RESPONSES, VALIDATION_ERROR_RESPONSES

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


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKTYPEn opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAKTYPE opvragen.",
        description="Een specifieke ZAAKTYPE opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKTYPE aan.",
        description=(
            "Maak een ZAAKTYPE aan.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- geldigheid `catalogus` URL, dit moet een catalogus binnen dezelfde API zijn\n"
            "- Uniciteit `catalogus` en `identificatie`. Dezelfde identificatie mag enkel "
            "opnieuw gebruikt worden als het zaaktype een andere geldigheidsperiode "
            "kent dan bestaande zaaktypen.\n"
            "- `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE."
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAKTYPE in zijn geheel bij.",
        description=(
            "Werk een ZAAKTYPE in zijn geheel bij. Dit kan alleen als het een concept "
            "betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKTYPE deels bij.",
        description=(
            "Werk een ZAAKTYPE deels bij. Dit kan alleen als het een concept betreft.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- `deelzaaktypen` moeten tot dezelfde catalogus behoren als het ZAAKTYPE."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKTYPE.",
        description="Verwijder een ZAAKTYPE. Dit kan alleen als het een concept betreft.",
    ),
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
    """

    queryset = (
        ZaakType.objects.prefetch_related(
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
        )
        .with_dates("identificatie")
        .order_by("-pk")
    )
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

    @extend_schema(
        "zaaktype_publish",
        summary="Publiceer het concept ZAAKTYPE.",
        description=(
            "Publiceren van het zaaktype zorgt ervoor dat dit in een Zaken API kan gebruikt "
            "worden. Na het publiceren van een zaaktype zijn geen inhoudelijke wijzigingen "
            "meer mogelijk - ook niet de statustypen, eigenschappen... etc. Indien er na het "
            "publiceren nog wat gewijzigd moet worden, dan moet je een nieuwe versie "
            "aanmaken."
        ),
        request=None,
        responses={
            status.HTTP_200_OK: ZaakTypeSerializer,
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"], name="zaaktype_publish")
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()

        related_errors = dict()

        # check related objects
        if (
            instance.besluittypen.filter(concept=True).exists()
            or instance.informatieobjecttypen.filter(concept=True).exists()
            or instance.deelzaaktypen.filter(concept=True).exists()
        ):
            msg = _("All related resources should be published")
            related_errors[api_settings.NON_FIELD_ERRORS_KEY] = [msg]

        has_invalid_resultaattypen = instance.resultaattypen.filter(
            selectielijstklasse=""
        ).exists()
        if has_invalid_resultaattypen:
            msg = _(
                "This zaaktype has resultaattypen without a selectielijstklasse. "
                "Please specify those before publishing the zaaktype."
            )
            related_errors["resultaattypen"] = [msg]

        num_roltypen = instance.roltype_set.count()
        if not num_roltypen >= 1:
            msg = _(
                "Publishing a zaaktype requires at least one roltype to be defined."
            )
            related_errors["roltypen"] = [msg]

        num_resultaattypen = instance.resultaattypen.count()
        if not num_resultaattypen >= 1:
            msg = _(
                "Publishing a zaaktype requires at least one resultaattype to be defined."
            )
            error_list = related_errors.get("resultaattypen", [])
            error_list.append(msg)
            related_errors["resultaattypen"] = error_list

        num_statustypen = instance.statustypen.count()
        if not num_statustypen >= 2:
            msg = _(
                "Publishing a zaaktype requires at least two statustypes to be defined."
            )
            related_errors["statustypen"] = [msg]

        if len(related_errors) > 0:
            print(related_errors)
            raise ValidationError(related_errors, code="concept-relation")

        return super()._publish(request, *args, **kwargs)
