# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.db import DatabaseError, transaction
from django.utils.translation import gettext_lazy as _

import structlog
from django_loose_fk.virtual_models import ProxyMixin
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from notifications_api_common.viewsets import (
    NotificationCreateMixin,
    NotificationDestroyMixin,
    NotificationViewSetMixin,
)
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from vng_api_common.audittrails.viewsets import (
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    AuditTrailViewsetMixin,
)
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.components.zaken.api.mixins import ClosedZaakMixin
from openzaak.components.zaken.api.utils import delete_remote_zaakbesluit
from openzaak.utils.api import delete_remote_oio
from openzaak.utils.data_filtering import ListFilterByAuthorizationsMixin
from openzaak.utils.mixins import CacheQuerysetMixin
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.views import AuditTrailViewSet

from ..models import Besluit, BesluitInformatieObject
from .audits import AUDIT_BRC
from .filters import BesluitFilter, BesluitInformatieObjectFilter
from .kanalen import KANAAL_BESLUITEN
from .permissions import BesluitAuthRequired
from .scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
    SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
    SCOPE_BESLUITEN_BIJWERKEN,
)
from .serializers import BesluitInformatieObjectSerializer, BesluitSerializer

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle BESLUITen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifiek BESLUIT opvragen.",
        description="Een specifiek BESLUIT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een BESLUIT aan.",
        description=(
            "Indien geen identificatie gegeven is, dan wordt deze automatisch "
            "gegenereerd.\n"
            "\n"
            "Er wordt gevalideerd op:\n"
            "- uniciteit van `verantwoorlijkeOrganisatie` + `identificatie`\n"
            "- geldigheid `verantwoorlijkeOrganisatie` RSIN\n"
            "- geldigheid `besluittype` URL - de resource moet opgevraagd kunnen "
            "worden uit de Catalogi API en de vorm van een BESLUITTYPE hebben.\n"
            "- geldigheid `zaak` URL - de resource moet opgevraagd kunnen worden "
            "uit de Zaken API en de vorm van een ZAAK hebben.\n"
            "- `datum` in het verleden of nu\n"
            "- publicatie `besluittype` - `concept` moet `false` zijn"
        ),
    ),
    update=extend_schema(
        summary="Werk een BESLUIT in zijn geheel bij.",
        description=(
            "Er wordt gevalideerd op:\n"
            "- uniciteit van `verantwoorlijkeOrganisatie` + `identificatie`\n"
            "- geldigheid `verantwoorlijkeOrganisatie` RSIN\n"
            "- het `besluittype` mag niet gewijzigd worden\n"
            "- geldigheid `zaak` URL - de resource moet opgevraagd kunnen worden "
            "uit de Zaken API en de vorm van een ZAAK hebben.\n"
            "- `datum` in het verleden of nu\n"
            "- publicatie `besluittype` - `concept` moet `false` zijn"
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een BESLUIT deels bij.",
        description=(
            "Er wordt gevalideerd op:\n"
            "- uniciteit van `verantwoorlijkeOrganisatie` + `identificatie`\n"
            "- geldigheid `verantwoorlijkeOrganisatie` RSIN\n"
            "- het `besluittype` mag niet gewijzigd worden\n"
            "- geldigheid `zaak` URL - de resource moet opgevraagd kunnen worden "
            "uit de Zaken API en de vorm van een ZAAK hebben.\n"
            "- `datum` in het verleden of nu\n"
            "- publicatie `besluittype` - `concept` moet `false` zijn"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een BESLUIT",
        description=(
            "Verwijder een BESLUIT samen met alle gerelateerde resources binnen deze API.\n"
            "\n"
            "**De gerelateerde resources zijn**\n"
            "- `BESLUITINFORMATIEOBJECT`\n"
            "- audit trail regels\n"
        ),
    ),
)
@conditional_retrieve()
class BesluitViewSet(
    CheckQueryParamsMixin,
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    ListFilterByAuthorizationsMixin,
    ClosedZaakMixin,
    viewsets.ModelViewSet,
):
    """Opvragen en bewerken van BESLUITen."""

    queryset = Besluit.objects.select_related("_besluittype").order_by("-pk")
    serializer_class = BesluitSerializer
    filterset_class = BesluitFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (BesluitAuthRequired,)
    required_scopes = {
        "list": SCOPE_BESLUITEN_ALLES_LEZEN,
        "retrieve": SCOPE_BESLUITEN_ALLES_LEZEN,
        "create": SCOPE_BESLUITEN_AANMAKEN,
        "destroy": SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
        "update": SCOPE_BESLUITEN_BIJWERKEN,
        "partial_update": SCOPE_BESLUITEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_BESLUITEN
    audit = AUDIT_BRC

    def perform_create(self, serializer):
        zaak = serializer.validated_data.get("zaak")
        if zaak and zaak.einddatum is not None:
            raise PermissionDenied(
                "Je mag geen gegevens aanpassen van een gesloten zaak."
            )

        instance = serializer.save()
        logger.info(
            "besluit_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info(
            "besluit_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        try:
            super().perform_destroy(instance)
        except DatabaseError as e:
            logger.error(
                "besluit_delete_failed",
                client_id=self.request.jwt_auth.client_id,
                uuid=uuid,
                error=str(e),
            )
            raise

        logger.info(
            "besluit_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )

        if isinstance(instance.zaak, ProxyMixin) and instance._zaakbesluit_url:
            try:
                delete_remote_zaakbesluit(instance._zaakbesluit_url)
            except Exception as exception:
                logger.error(
                    "delete_remote_zaakbesluit_failed",
                    client_id=self.request.jwt_auth.client_id,
                    uuid=uuid,
                    error=str(exception),
                    zaakbesluit_url=instance._zaakbesluit_url,
                )
                raise ValidationError(
                    {
                        "zaak": _(
                            "Could not delete remote relation: {}".format(exception)
                        )
                    },
                    code="pending-relations",
                )


@extend_schema_view(
    list=extend_schema(
        summary="Alle BESLUIT-INFORMATIEOBJECT relaties opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke BESLUIT-INFORMATIEOBJECT relatie opvragen.",
        description="Een specifieke BESLUIT-INFORMATIEOBJECT relatie opvragen.",
    ),
    create=extend_schema(
        summary="Maak een BESLUIT-INFORMATIEOBJECT relatie aan.",
        description=(
            "Registreer een INFORMATIEOBJECT bij een BESLUIT. Er worden twee types van "
            "relaties met andere objecten gerealiseerd:\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- geldigheid `besluit` URL\n"
            "- geldigheid `informatieobject` URL\n"
            "- de combinatie `informatieobject` en `besluit` moet uniek zijn\n"
            "\n"
            "**Opmerkingen**\n"
            "- De `registratiedatum` wordt door het systeem op 'NU' gezet. De "
            "`aardRelatie` wordt ook door het systeem gezet.\n"
            "- Bij het aanmaken wordt ook in de Documenten API de gespiegelde relatie "
            "aangemaakt, echter zonder de relatie-informatie."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een BESLUIT-INFORMATIEOBJECT relatie.",
        description="Verwijder een BESLUIT-INFORMATIEOBJECT relatie.",
    ),
)
@conditional_retrieve()
class BesluitInformatieObjectViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    NotificationDestroyMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """Opvragen en bewerken van BESLUIT-INFORMATIEOBJECT relaties."""

    queryset = (
        BesluitInformatieObject.objects.select_related("besluit", "_informatieobject")
        .prefetch_related("_informatieobject__enkelvoudiginformatieobject_set")
        .all()
    )
    serializer_class = BesluitInformatieObjectSerializer
    filterset_class = BesluitInformatieObjectFilter
    lookup_field = "uuid"
    permission_classes = (BesluitAuthRequired,)
    permission_main_object = "besluit"
    required_scopes = {
        "list": SCOPE_BESLUITEN_ALLES_LEZEN,
        "retrieve": SCOPE_BESLUITEN_ALLES_LEZEN,
        "create": SCOPE_BESLUITEN_AANMAKEN,
        "destroy": SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
    }
    notifications_kanaal = KANAAL_BESLUITEN
    notifications_main_resource_key = "besluit"
    audit = AUDIT_BRC

    @property
    def notifications_wrap_in_atomic_block(self):
        # do not wrap the outermost create/destroy in atomic transaction blocks to send
        # notifications. The serializer wraps the actual object creation into a single
        # transaction, and after that, we're in autocommit mode.
        # Once the response has been properly obtained (success), then the notification
        # gets scheduled, and because of the transaction being in autocommit mode at that
        # point, the notification sending will fire immediately.
        if self.action in ["create", "destroy"]:
            return False
        return super().notifications_wrap_in_atomic_block

    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info(
            "besluitinformatieobject_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        with transaction.atomic():
            try:
                super().perform_destroy(instance)
            except DatabaseError as e:
                logger.error(
                    "besluitinformatieobject_delete_failed",
                    client_id=self.request.jwt_auth.client_id,
                    uuid=uuid,
                    error=str(e),
                )
                raise
            logger.info(
                "besluitinformatieobject_deleted",
                client_id=self.request.jwt_auth.client_id,
                uuid=uuid,
            )

        if (
            isinstance(instance.informatieobject, ProxyMixin)
            and instance._objectinformatieobject_url
        ):
            try:
                delete_remote_oio(instance._objectinformatieobject_url)
            except Exception as exception:
                logger.error(
                    "delete_remote_oio_failed",
                    client_id=self.request.jwt_auth.client_id,
                    uuid=uuid,
                    error=str(exception),
                    objectinformatieobject_url=instance._objectinformatieobject_url,
                )
                instance.save()
                raise ValidationError(
                    {
                        "informatieobject": _(
                            "Could not delete remote relation: {}".format(exception)
                        )
                    },
                    code="pending-relations",
                )


@extend_schema_view(
    list=extend_schema(
        summary="Alle audit trail regels behorend bij het BESLUIT.",
        description="Alle audit trail regels behorend bij het BESLUIT.",
        parameters=[
            OpenApiParameter("besluit_uuid", OpenApiTypes.UUID, OpenApiParameter.PATH)
        ],
    ),
    retrieve=extend_schema(
        summary="Een specifieke audit trail regel opvragen.",
        description="Een specifieke audit trail",
        parameters=[
            OpenApiParameter("besluit_uuid", OpenApiTypes.UUID, OpenApiParameter.PATH)
        ],
    ),
)
class BesluitAuditTrailViewSet(AuditTrailViewSet):
    """Opvragen van de audit trail regels."""

    main_resource_lookup_field = "besluit_uuid"
    permission_classes = (AuthRequired,)
