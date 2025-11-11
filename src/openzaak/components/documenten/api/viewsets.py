# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import structlog
from django_loose_fk.virtual_models import ProxyMixin
from django_sendfile import sendfile
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from notifications_api_common.viewsets import NotificationViewSetMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.serializers import ErrorDetail, ValidationError
from rest_framework.settings import api_settings
from vng_api_common.audittrails.viewsets import (
    AuditTrailMixin,
    AuditTrailViewsetMixin,
)
from vng_api_common.caching import conditional_retrieve
from vng_api_common.constants import CommonResourceAction
from vng_api_common.filters_backend import Backend
from vng_api_common.search import SearchMixin
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.components.documenten.import_utils import DocumentRow
from openzaak.components.documenten.tasks import import_documents
from openzaak.import_data.models import ImportStatusChoices, ImportTypeChoices
from openzaak.import_data.views import (
    ImportCreateview,
    ImportDestroyView,
    ImportReportView,
    ImportStatusView,
    ImportUploadView,
)
from openzaak.notifications.viewsets import (
    MultipleNotificationMixin,
)
from openzaak.utils.data_filtering import ListFilterByAuthorizationsMixin
from openzaak.utils.help_text import mark_experimental
from openzaak.utils.mixins import (
    CacheQuerysetMixin,
    ExpandMixin,
)
from openzaak.utils.pagination import OptimizedPagination
from openzaak.utils.permissions import AuthRequired
from openzaak.utils.schema import (
    COMMON_ERROR_RESPONSES,
    FILE_ERROR_RESPONSES,
    VALIDATION_ERROR_RESPONSES,
)
from openzaak.utils.views import AuditTrailViewSet

from ...zaken.api.audits import AUDIT_ZRC
from ...zaken.api.kanalen import KANAAL_ZAKEN
from ...zaken.api.mixins import ClosedZaakMixin
from ...zaken.api.scopes import (
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from ...zaken.models import ZaakInformatieObject
from ..models import (
    BestandsDeel,
    EnkelvoudigInformatieObject,
    Gebruiksrechten,
    ObjectInformatieObject,
    ReservedDocument,
    Verzending,
)
from .audits import AUDIT_DRC
from .filters import (
    EnkelvoudigInformatieObjectDetailFilter,
    EnkelvoudigInformatieObjectListFilter,
    GebruiksrechtenDetailFilter,
    GebruiksrechtenFilter,
    ObjectInformatieObjectFilter,
    VerzendingDetailFilter,
    VerzendingFilter,
)
from .kanalen import KANAAL_DOCUMENTEN
from .mixins import UpdateWithoutPartialMixin
from .permissions import (
    DocumentRegistrerenAuthRequired,
    InformationObjectAuthRequired,
)
from .renderers import BinaryFileRenderer
from .scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
    SCOPE_DOCUMENTEN_LOCK,
)
from .serializers import (
    BestandsDeelSerializer,
    DocumentRegistrerenSerializer,
    EIOZoekSerializer,
    EnkelvoudigInformatieObjectCreateLockSerializer,
    EnkelvoudigInformatieObjectSerializer,
    EnkelvoudigInformatieObjectWithLockSerializer,
    GebruiksrechtenSerializer,
    LockEnkelvoudigInformatieObjectSerializer,
    ObjectInformatieObjectSerializer,
    ReservedDocumentSerializer,
    UnlockEnkelvoudigInformatieObjectSerializer,
    VerzendingSerializer,
)
from .utils import generate_document_identificatie
from .validators import CreateRemoteRelationValidator, RemoteRelationValidator

logger = structlog.stdlib.get_logger(__name__)

# Openapi query parameters for version querying
VERSIE_QUERY_PARAM = OpenApiParameter(
    "versie",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description="Het (automatische) versienummer van het INFORMATIEOBJECT.",
)
REGISTRATIE_QUERY_PARAM = OpenApiParameter(
    "registratieOp",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description=(
        "Een datumtijd in ISO8601 formaat. De versie van het INFORMATIEOBJECT die qua `begin_registratie` het "
        "kortst hiervoor zit wordt opgehaald."
    ),
)


@extend_schema_view(
    list=extend_schema(
        summary="Alle (ENKELVOUDIGe) INFORMATIEOBJECTen opvragen.",
        description=(
            "Deze lijst kan gefilterd wordt met query-string parameters.\n"
            "\n"
            "De objecten bevatten metadata over de documenten en de downloadlink "
            "(`inhoud`) naar de binary data. Alleen de laatste versie van elk "
            "(ENKELVOUDIG) INFORMATIEOBJECT wordt getoond. Specifieke versies kunnen "
            "alleen"
        ),
    ),
    retrieve=extend_schema(
        summary="Een specifiek (ENKELVOUDIG) INFORMATIEOBJECT opvragen.",
        description=(
            "Het object bevat metadata over het document en de downloadlink (`inhoud`) "
            "naar de binary data. Dit geeft standaard de laatste versie van het "
            "(ENKELVOUDIG) INFORMATIEOBJECT. Specifieke versies kunnen middels "
            "query-string parameters worden opgevraagd."
        ),
        parameters=[VERSIE_QUERY_PARAM, REGISTRATIE_QUERY_PARAM],
    ),
    create=extend_schema(
        summary="Maak een (ENKELVOUDIG) INFORMATIEOBJECT aan.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen "
            "worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.\n"
            "- publicatie `informatieobjecttype` - `concept` moet `false` zijn"
        ),
        responses={
            status.HTTP_201_CREATED: EnkelvoudigInformatieObjectSerializer,
            **COMMON_ERROR_RESPONSES,
            **VALIDATION_ERROR_RESPONSES,
            **FILE_ERROR_RESPONSES,
        },
    ),
    update=extend_schema(
        summary="Werk een (ENKELVOUDIG) INFORMATIEOBJECT in zijn geheel bij.",
        description=(
            "Dit creëert altijd een nieuwe versie van het (ENKELVOUDIG) INFORMATIEOBJECT.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- correcte `lock` waarde\n"
            "- geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen "
            "worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.\n"
            "- publicatie `informatieobjecttype` - `concept` moet `false` zijn\n"
            "- status NIET `definitief`"
        ),
        responses={
            status.HTTP_200_OK: EnkelvoudigInformatieObjectSerializer,
            **COMMON_ERROR_RESPONSES,
            **VALIDATION_ERROR_RESPONSES,
            **FILE_ERROR_RESPONSES,
        },
    ),
    partial_update=extend_schema(
        summary="Werk een (ENKELVOUDIG) INFORMATIEOBJECT deels bij.",
        description=(
            "Dit creëert altijd een nieuwe versie van het (ENKELVOUDIG) INFORMATIEOBJECT.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- correcte `lock` waarde\n"
            "- geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen "
            "worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.\n"
            "- publicatie `informatieobjecttype` - `concept` moet `false` zijn\n"
            "- status NIET `definitief`"
        ),
        responses={
            status.HTTP_200_OK: EnkelvoudigInformatieObjectSerializer,
            **COMMON_ERROR_RESPONSES,
            **VALIDATION_ERROR_RESPONSES,
            **FILE_ERROR_RESPONSES,
        },
    ),
    destroy=extend_schema(
        summary="Verwijder een (ENKELVOUDIG) INFORMATIEOBJECT.",
        description=(
            "Verwijder een (ENKELVOUDIG) INFORMATIEOBJECT en alle bijbehorende versies, "
            "samen met alle gerelateerde resources binnen deze API. Dit is alleen mogelijk "
            "als er geen OBJECTINFORMATIEOBJECTen relateerd zijn aan het (ENKELVOUDIG) "
            "INFORMATIEOBJECT.\n"
            "\n"
            "**Gerelateerde resources**\n"
            "- GEBRUIKSRECHTen\n"
            "- audit trail regels\n"
        ),
    ),
)
@conditional_retrieve()
class EnkelvoudigInformatieObjectViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    SearchMixin,
    ExpandMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailViewsetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van (ENKELVOUDIG) INFORMATIEOBJECTen (documenten).
    """

    queryset = (
        EnkelvoudigInformatieObject.objects.select_related(
            "canonical", "_informatieobjecttype"
        )
        .prefetch_related("canonical__bestandsdelen")
        .order_by("canonical", "-versie")
        .distinct("canonical")
    )
    lookup_field = "uuid"
    serializer_class = EnkelvoudigInformatieObjectSerializer
    search_input_serializer_class = EIOZoekSerializer
    filter_backends = (Backend,)
    permission_classes = (InformationObjectAuthRequired,)
    required_scopes = {
        "list": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "retrieve": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "create": SCOPE_DOCUMENTEN_AANMAKEN,
        "destroy": SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        "update": SCOPE_DOCUMENTEN_BIJWERKEN,
        "partial_update": SCOPE_DOCUMENTEN_BIJWERKEN,
        "download": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "lock": SCOPE_DOCUMENTEN_LOCK,
        "unlock": SCOPE_DOCUMENTEN_LOCK | SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
        "_zoek": SCOPE_DOCUMENTEN_ALLES_LEZEN,
    }
    notifications_kanaal = KANAAL_DOCUMENTEN
    audit = AUDIT_DRC

    def get_renderers(self):
        if self.action == "download":
            return [BinaryFileRenderer]
        return super().get_renderers()

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.has_references():
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "All relations to the document must be destroyed before destroying the document"
                    )
                },
                code="pending-relations",
            )

        if instance.canonical.lock:
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "Locked objects cannot be destroyed"
                    )
                },
                code="destroy-locked",
            )

        instance.destroy()

    @property
    def filterset_class(self):
        """
        To support filtering by versie and registratieOp for detail view
        """
        if self.detail:
            return EnkelvoudigInformatieObjectDetailFilter
        return EnkelvoudigInformatieObjectListFilter

    def get_serializer_class(self):
        """
        To validate that a lock id is sent only with PUT and PATCH operations
        """
        action = getattr(self, "action", None)
        if action in ["update", "partial_update"]:
            return EnkelvoudigInformatieObjectWithLockSerializer
        elif action == "create":
            return EnkelvoudigInformatieObjectCreateLockSerializer
        return super().get_serializer_class()

    @property
    def pagination_class(self):
        return OptimizedPagination

    @extend_schema(
        "enkelvoudiginformatieobject_download",
        summary="Download de binaire data van het (ENKELVOUDIG) INFORMATIEOBJECT.",
        description="Download de binaire data van het (ENKELVOUDIG) INFORMATIEOBJECT.",
        parameters=[VERSIE_QUERY_PARAM, REGISTRATIE_QUERY_PARAM],
        responses={
            (status.HTTP_200_OK, "application/octet-stream"): OpenApiResponse(
                description="De binaire bestandsinhoud",
                response=OpenApiTypes.BINARY,
            ),
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(methods=["get"], detail=True, name="enkelvoudiginformatieobject_download")
    def download(self, request, *args, **kwargs):
        eio = self.get_object()
        return sendfile(
            request,
            eio.inhoud.path,
            attachment=True,
            mimetype="application/octet-stream",
        )

    @extend_schema(
        "enkelvoudiginformatieobject_lock",
        summary="Vergrendel een (ENKELVOUDIG) INFORMATIEOBJECT.",
        description=(
            'Voert een "checkout" uit waardoor het (ENKELVOUDIG) INFORMATIEOBJECT '
            "vergrendeld wordt met een `lock` waarde. Alleen met deze waarde kan het "
            "(ENKELVOUDIG) INFORMATIEOBJECT bijgewerkt (`PUT`, `PATCH`) en weer "
            "ontgrendeld worden."
        ),
        request=LockEnkelvoudigInformatieObjectSerializer,
        responses={
            status.HTTP_200_OK: LockEnkelvoudigInformatieObjectSerializer,
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"], name="enkelvoudiginformatieobject_lock")
    def lock(self, request, *args, **kwargs):
        eio = self.get_object()
        canonical = eio.canonical
        lock_serializer = LockEnkelvoudigInformatieObjectSerializer(
            canonical,
            data=request.data,
            context={"request": request, "uuid": kwargs.get("uuid")},
        )
        lock_serializer.is_valid(raise_exception=True)
        lock_serializer.save()
        return Response(lock_serializer.data)

    @extend_schema(
        "enkelvoudiginformatieobject_unlock",
        summary="Ontgrendel een (ENKELVOUDIG) INFORMATIEOBJECT.",
        description=(
            'Heft de "checkout" op waardoor het (ENKELVOUDIG) INFORMATIEOBJECT '
            "ontgrendeld wordt."
        ),
        request=UnlockEnkelvoudigInformatieObjectSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: None,
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"], name="enkelvoudiginformatieobject_unlock")
    def unlock(self, request, *args, **kwargs):
        eio = self.get_object()
        eio_data = self.get_serializer(eio).data

        # check if it's a force unlock by administrator
        force_unlock = False
        if self.request.jwt_auth.has_auth(
            scopes=SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
            informatieobjecttype=eio_data["informatieobjecttype"],
            vertrouwelijkheidaanduiding=eio_data["vertrouwelijkheidaanduiding"],
            init_component=self.queryset.model._meta.app_label,
        ):
            force_unlock = True

        unlock_serializer = UnlockEnkelvoudigInformatieObjectSerializer(
            eio,
            data=request.data,
            context={
                "request": request,
                "force_unlock": force_unlock,
                "uuid": kwargs.get("uuid"),
            },
        )
        unlock_serializer.is_valid(raise_exception=True)
        unlock_serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        "enkelvoudiginformatieobject__zoek",
        summary="Voer een zoekopdracht uit op (ENKELVOUDIG) INFORMATIEOBJECTen.",
        description=(
            "Zoeken/filteren gaat normaal via de `list` operatie, deze is echter "
            "niet geschikt voor zoekopdrachten met UUIDs."
        ),
        responses={
            status.HTTP_200_OK: EnkelvoudigInformatieObjectSerializer(many=True),
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(methods=["post"], detail=False, name="enkelvoudiginformatieobject__zoek")
    def _zoek(self, request, *args, **kwargs):
        """
        Voer een zoekopdracht uit op (ENKELVOUDIG) INFORMATIEOBJECTen .

        Zoeken/filteren gaat normaal via de `list` operatie, deze is echter
        niet geschikt voor zoekopdrachten met UUIDs.
        """
        if not request.data:
            err = ErrorDetail(
                _("Search parameters must be specified"), code="empty_search_body"
            )
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: err})

        search_input = self.get_search_input()
        queryset = self.filter_queryset(self.get_queryset())

        for name, value in search_input.items():
            queryset = queryset.filter(**{name: value})

        return self.get_search_output(queryset)

    _zoek.is_search_action = True

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "enkelvoudiginformatieobject_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "enkelvoudiginformatieobject_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )


@extend_schema_view(
    create=extend_schema(
        operation_id="enkelvoudiginformatieobject_import_create",
        summary=_("Een IMPORT creeren"),
        description=mark_experimental(
            "Creëert een IMPORT. Wanneer er vervolgens een metadata bestand "
            " wordt aangeleverd zal de daadwerkelijke IMPORT van start gaan. Voor deze actie is een APPLICATIE nodig met "
            "`heeft_alle_autorisaties` ingeschakeld."
        ),
        request=OpenApiTypes.NONE,
    )
)
class EnkelvoudigInformatieObjectImportView(ImportCreateview):
    import_type = ImportTypeChoices.documents

    required_scopes = {}


def _get_import_headers():
    return ", ".join([f"**{header}**" for header in DocumentRow.import_headers])


@extend_schema_view(
    create=extend_schema(
        operation_id="enkelvoudiginformatieobject_import_upload",
        summary=_("Een IMPORT bestand uploaden"),
        description=mark_experimental(
            "Het uploaden van een metadata bestand, ter gebruik voor de IMPORT. "
            "Deze actie start tevens de IMPORT. Één actieve IMPORT "
            " tegelijkertijd is mogelijk. De volgende kolommen worden verwacht "
            f"(op volgorde) in het bestand: {_get_import_headers()}. Voor deze "
            "actie is een APPLICATIE nodig met `heeft_alle_autorisaties` ingeschakeld."
        ),
        request={"text/csv": OpenApiTypes.BYTE},
        parameters=[
            OpenApiParameter(
                name="Content-Type",
                required=True,
                location=OpenApiParameter.HEADER,
                description="Content type van de verzoekinhoud.",
                type=OpenApiTypes.STR,
                enum=["test/csv"],
            )
        ],
        responses={
            status.HTTP_200_OK: OpenApiResponse(description=_("No response body")),
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
        },
    )
)
class EnkelvoudigInformatieObjectImportUploadView(ImportUploadView):
    import_type = ImportTypeChoices.documents
    import_headers = DocumentRow.import_headers

    required_scopes = {}

    @property
    def import_dir(self) -> Path:
        return Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        request_headers = {
            key: value
            for key, value in request.META.items()
            if isinstance(value, (str, int))
        }

        import_instance = self.get_object()
        import_documents.delay(import_instance.pk, request_headers)

        return response


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="enkelvoudiginformatieobject_import_status",
        summary=_("De status van een IMPORT opvragen."),
        description=mark_experimental(
            "Het opvragen van de status van een IMPORT. "
            "Voor deze actie is een APPLICATIE nodig met `heeft_alle_autorisaties`"
            " ingeschakeld."
        ),
    )
)
class EnkelvoudigInformatieObjectImportStatusView(ImportStatusView):
    import_type = ImportTypeChoices.documents

    required_scopes = {}


def _get_report_headers():
    return ", ".join([f"**{header}**" for header in DocumentRow.export_headers])


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="enkelvoudiginformatieobject_import_report",
        summary=_("Het reportage bestand van een IMPORT downloaden."),
        description=mark_experimental(
            "Het reportage bestand downloaden van een IMPORT. Dit bestand is alleen "
            "beschikbaar indien de IMPORT is afgerond (ongeacht het resultaat). "
            "De volgende kolommen zijn te vinden in het rapportage "
            f"bestand: {_get_report_headers()}. Voor deze actie is een APPLICATIE "
            "nodig met `heeft_alle_autorisaties` ingeschakeld."
        ),
        responses={
            (status.HTTP_200_OK, "text/csv"): {
                "type": "string",
                "description": _("Het reportage bestand van de IMPORT."),
            },
            **COMMON_ERROR_RESPONSES,
        },
    )
)
class EnkelvoudigInformatieObjectImportReportView(ImportReportView):
    import_type = ImportTypeChoices.documents

    required_scopes = {}


def _get_deletion_choices():
    return ", ".join(
        sorted(
            [f"**{choice.value}**" for choice in ImportStatusChoices.deletion_choices]
        )
    )


@extend_schema_view(
    destroy=extend_schema(
        operation_id="enkelvoudiginformatieobject_import_destroy",
        summary=_("Een IMPORT verwijderen."),
        description=mark_experimental(
            "Een IMPORT verwijderen. Het verwijderen van een IMPORT "
            "is alleen mogelijk wanneer deze een van de volgende statussen heeft: "
            f"{_get_deletion_choices()}. Voor deze actie is een "
            "APPLICATIE nodig met `heeft_alle_autorisaties` ingeschakeld."
        ),
        responses={
            status.HTTP_204_NO_CONTENT: None,
            **COMMON_ERROR_RESPONSES,
        },
    )
)
class EnkelvoudigInformatieObjectImportDestroyView(ImportDestroyView):
    import_type = ImportTypeChoices.documents

    required_scopes = {}


@extend_schema_view(
    list=extend_schema(
        summary="Alle GEBRUIKSRECHTen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke GEBRUIKSRECHT opvragen.",
        description="Een specifieke GEBRUIKSRECHT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een GEBRUIKSRECHT aan.",
        description=(
            "Voeg GEBRUIKSRECHTen toe voor een INFORMATIEOBJECT.\n"
            "\n"
            "**Opmerkingen**\n"
            "- Het toevoegen van gebruiksrechten zorgt ervoor dat de "
            "`indicatieGebruiksrecht` op het informatieobject op `true` gezet wordt."
        ),
    ),
    update=extend_schema(
        summary="Werk een GEBRUIKSRECHT in zijn geheel bij.",
        description="Werk een GEBRUIKSRECHT in zijn geheel bij.",
    ),
    partial_update=extend_schema(
        summary="Werk een GEBRUIKSRECHT relatie deels bij.",
        description="Werk een GEBRUIKSRECHT relatie deels bij.",
    ),
    destroy=extend_schema(
        summary="Verwijder een GEBRUIKSRECHT.",
        description=(
            "**Opmerkingen**\n"
            "- Indien het laatste GEBRUIKSRECHT van een INFORMATIEOBJECT verwijderd "
            "wordt, dan wordt de `indicatieGebruiksrecht` van het INFORMATIEOBJECT op "
            "`null` gezet."
        ),
    ),
)
@conditional_retrieve()
class GebruiksrechtenViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ExpandMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailViewsetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van GEBRUIKSRECHTen bij een INFORMATIEOBJECT.
    """

    queryset = (
        Gebruiksrechten.objects.select_related("informatieobject")
        .prefetch_related("informatieobject__enkelvoudiginformatieobject_set")
        .all()
    )
    serializer_class = GebruiksrechtenSerializer
    lookup_field = "uuid"
    notifications_kanaal = KANAAL_DOCUMENTEN
    notifications_main_resource_key = "informatieobject"
    permission_classes = (InformationObjectAuthRequired,)
    permission_main_object = "informatieobject"
    required_scopes = {
        "list": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "retrieve": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "create": SCOPE_DOCUMENTEN_AANMAKEN,
        "destroy": SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        "update": SCOPE_DOCUMENTEN_BIJWERKEN,
        "partial_update": SCOPE_DOCUMENTEN_BIJWERKEN,
    }
    audit = AUDIT_DRC
    audittrail_main_resource_key = "informatieobject"

    @property
    def filterset_class(self):
        """
        To support expand
        """
        if self.detail:
            return GebruiksrechtenDetailFilter
        return GebruiksrechtenFilter

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "gebruiksrechten_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "gebruiksrechten_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        instance.delete()
        logger.info(
            "gebruiksrechten_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle audit trail regels behorend bij het INFORMATIEOBJECT.",
        description="Alle audit trail regels behorend bij het INFORMATIEOBJECT.",
        parameters=[
            OpenApiParameter(
                "enkelvoudiginformatieobject_uuid",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Een specifieke audit trail regel opvragen.",
        description="Een specifieke audit trail regel opvragen.",
        parameters=[
            OpenApiParameter(
                "enkelvoudiginformatieobject_uuid",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
            )
        ],
    ),
)
class EnkelvoudigInformatieObjectAuditTrailViewSet(AuditTrailViewSet):
    """Opvragen van de audit trail regels."""

    main_resource_lookup_field = "enkelvoudiginformatieobject_uuid"
    permission_classes = (AuthRequired,)


@extend_schema_view(
    list=extend_schema(
        summary="Alle OBJECT-INFORMATIEOBJECT relaties opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke OBJECT-INFORMATIEOBJECT relatie opvragen.",
        description="Een specifieke OBJECT-INFORMATIEOBJECT relatie opvragen.",
    ),
    create=extend_schema(
        summary="Maak een OBJECT-INFORMATIEOBJECT relatie aan.",
        description=(
            "**LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**\n"
            "\n"
            "Andere API's, zoals de Zaken API en de Besluiten API, gebruiken dit "
            "endpoint bij het synchroniseren van relaties.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- geldigheid `informatieobject` URL\n"
            "- de combinatie `informatieobject` en `object` moet uniek zijn\n"
            "- bestaan van `object` URL"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een OBJECT-INFORMATIEOBJECT relatie.",
        description=(
            "**LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**\n"
            "\n"
            "Andere API's, zoals de Zaken API en de Besluiten API, gebruiken dit "
            "endpoint bij het synchroniseren van relaties."
        ),
    ),
)
@conditional_retrieve()
class ObjectInformatieObjectViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en verwijderen van OBJECT-INFORMATIEOBJECT relaties.

    Het betreft een relatie tussen een willekeurig OBJECT, bijvoorbeeld een
    ZAAK in de Zaken API, en een INFORMATIEOBJECT.
    """

    queryset = (
        ObjectInformatieObject.objects.select_related(
            "_zaak", "_besluit", "informatieobject"
        )
        .prefetch_related("informatieobject__enkelvoudiginformatieobject_set")
        .all()
    )
    serializer_class = ObjectInformatieObjectSerializer
    filterset_class = ObjectInformatieObjectFilter
    lookup_field = "uuid"
    permission_classes = (InformationObjectAuthRequired,)
    permission_main_object = "informatieobject"
    required_scopes = {
        "list": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "retrieve": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "create": SCOPE_DOCUMENTEN_AANMAKEN,
        "destroy": SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        "update": SCOPE_DOCUMENTEN_BIJWERKEN,
        "partial_update": SCOPE_DOCUMENTEN_BIJWERKEN,
    }

    def perform_create(self, serializer):
        informatieobject = serializer.validated_data["informatieobject"]
        object = serializer.validated_data["object"]
        object_type = serializer.validated_data["object_type"]

        # external object
        if isinstance(object, (ProxyMixin, str)):
            # Validate that the remote relation exists
            validator = CreateRemoteRelationValidator(request=self.request)
            try:
                validator(informatieobject, object, object_type)
            except ValidationError as exc:
                raise ValidationError(
                    {api_settings.NON_FIELD_ERRORS_KEY: exc}, code=exc.detail[0].code
                ) from exc

            super().perform_create(serializer)
            logger.info(
                "objectinformatieobject_created",
                client_id=self.request.jwt_auth.client_id,
                informatieobject=str(informatieobject),
                object=str(object),
                object_type=str(object_type),
            )
            return
        # object was already created by BIO/ZIO creation,
        # so just set the instance
        try:
            serializer.instance = self.get_queryset().get(
                **{
                    serializer.validated_data["object_type"]: serializer.validated_data[
                        "object"
                    ],
                    "informatieobject": serializer.validated_data["informatieobject"],
                }
            )
        except ObjectInformatieObject.DoesNotExist:
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The relation between object and informatieobject doesn't exist"
                    )
                },
                code="inconsistent-relation",
            )

    def perform_destroy(self, instance):
        """
        The actual relation information must be updated in the signals,
        so this is just a check.
        """
        validator = RemoteRelationValidator(request=self.request)
        try:
            validator(instance)
        except ValidationError as exc:
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: exc}, code=exc.detail[0].code
            ) from exc

        if isinstance(instance.object, (ProxyMixin, str)):
            super().perform_destroy(instance)
            logger.info(
                "objectinformatieobject_deleted",
                client_id=self.request.jwt_auth.client_id,
                uuid=str(instance.uuid),
                object=str(instance.object),
            )


@extend_schema_view(update=extend_schema(summary="Upload een bestandsdeel"))
class BestandsDeelViewSet(UpdateWithoutPartialMixin, viewsets.GenericViewSet):
    queryset = BestandsDeel.objects.all()
    serializer_class = BestandsDeelSerializer
    lookup_field = "uuid"
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (InformationObjectAuthRequired,)
    permission_main_object = "informatieobject"
    required_scopes = {
        "update": SCOPE_DOCUMENTEN_BIJWERKEN,
    }

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "bestandsdeel_uploaded",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle VERZENDINGen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke VERZENDING opvragen.",
        description="Een specifieke VERZENDING opvragen.",
    ),
    create=extend_schema(
        summary="Maak een VERZENDING aan.",
        description=" Voeg VERZENDINGen toe voor een INFORMATIEOBJECT en een BETROKKENE.",
    ),
    update=extend_schema(
        summary="Werk een VERZENDING in zijn geheel bij.",
        description="Werk een VERZENDING in zijn geheel bij.",
    ),
    partial_update=extend_schema(
        summary="Werk een VERZENDING relatie deels bij.",
        description="Werk een VERZENDING relatie deels bij.",
    ),
    destroy=extend_schema(
        summary="Verwijder een VERZENDING.", description="Verwijder een VERZENDING."
    ),
)
@conditional_retrieve()
class VerzendingViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    ExpandMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    # in the OAS there are no additional audittrail endpoints for verzending
    # AuditTrailViewsetMixin,
    viewsets.ModelViewSet,
):
    """Opvragen en bewerken van VERZENDINGen."""

    queryset = Verzending.objects.select_related("informatieobject").order_by("-pk")
    serializer_class = VerzendingSerializer
    pagination_class = OptimizedPagination
    lookup_field = "uuid"
    notifications_kanaal = KANAAL_DOCUMENTEN
    notifications_main_resource_key = "informatieobject"
    permission_classes = (InformationObjectAuthRequired,)
    permission_main_object = "informatieobject"
    required_scopes = {
        "list": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "retrieve": SCOPE_DOCUMENTEN_ALLES_LEZEN,
        "create": SCOPE_DOCUMENTEN_AANMAKEN,
        "destroy": SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        "update": SCOPE_DOCUMENTEN_BIJWERKEN,
        "partial_update": SCOPE_DOCUMENTEN_BIJWERKEN,
    }

    @property
    def filterset_class(self):
        """
        To support expand
        """
        if self.detail:
            return VerzendingDetailFilter
        return VerzendingFilter

    def perform_create(self, serializer):
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "verzending_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=instance.uuid,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)

        instance = serializer.instance

        logger.info(
            "verzending_updated",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)

        super().perform_destroy(instance)

        logger.info(
            "verzending_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )


class ReservedDocumentViewSet(viewsets.ViewSet):
    queryset = ReservedDocument.objects.all()
    serializer_class = ReservedDocumentSerializer
    permission_classes = (AuthRequired,)
    required_scopes = {
        "create": SCOPE_DOCUMENTEN_AANMAKEN,
    }

    @extend_schema(
        summary="Reserveer een documentnummer",
        description=mark_experimental(
            "Reserveer een documentnummer binnen een specifieke bronorganisatie "
            "zonder direct een informatieobject aan te maken. "
            "Dit documentnummer zal toegekend worden aan het eerstvolgende "
            "EnkelvoudigInformatieObject dat met dit documentnummer wordt aangemaakt "
            "binnen de bronorganisatie en het documentnummer kan daarna niet hergebruikt worden"
        ),
        request=ReservedDocumentSerializer,
        examples=[
            OpenApiExample(
                "Enkele reservering",
                value={"identificatie": "DOCUMENT-2025-0000000001"},
                response_only=True,
            ),
            OpenApiExample(
                "Meerdere reserveringen",
                value=[
                    {"identificatie": "DOCUMENT-2025-0000000001"},
                    {"identificatie": "DOCUMENT-2025-0000000002"},
                ],
                response_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        bronorganisatie = serializer.validated_data["bronorganisatie"]
        aantal = serializer.validated_data.get("aantal", 1)

        today = date.today()
        identificaties = generate_document_identificatie(
            bronorganisatie=bronorganisatie,
            date_value=today,
            aantal=aantal,
        )

        output_data = self.create_reserved_documents(
            bronorganisatie, identificaties, aantal
        )

        return Response(output_data, status=status.HTTP_201_CREATED)

    def create_reserved_documents(self, bronorganisatie, identificaties, aantal):
        if aantal == 1:
            instance = ReservedDocument.objects.create(
                identificatie=identificaties,
                bronorganisatie=bronorganisatie,
            )
            logger.info(
                "reserved_document_created",
                client_id=self.request.jwt_auth.client_id,
                bronorganisatie=instance.bronorganisatie,
                identificatie=instance.identificatie,
                aantal=1,
            )
            output_serializer = self.serializer_class(instance)
            return output_serializer.data
        else:
            instances = [
                ReservedDocument(identificatie=ident, bronorganisatie=bronorganisatie)
                for ident in identificaties
            ]
            ReservedDocument.objects.bulk_create(instances)
            logger.info(
                "reserved_document_created_bulk",
                client_id=self.request.jwt_auth.client_id,
                bronorganisatie=bronorganisatie,
                aantal=aantal,
                identificaties=[inst.identificatie for inst in instances],
            )
            output_serializer = self.serializer_class(instances, many=True)
            return output_serializer.data


@extend_schema(
    summary="Registreer een document",
    description=mark_experimental(
        "Maak een EnkelvoudigInformatieObject en een ZaakInformatieObject aan om het document direct aan een zaak te linken."
    ),
)
class DocumentRegistrerenViewSet(
    viewsets.ViewSet,
    MultipleNotificationMixin,
    ClosedZaakMixin,
    AuditTrailMixin,
):
    serializer_class = DocumentRegistrerenSerializer
    permission_classes = (DocumentRegistrerenAuthRequired,)

    required_scopes = {
        "create": SCOPE_DOCUMENTEN_AANMAKEN
        & (
            SCOPE_ZAKEN_CREATE
            | SCOPE_ZAKEN_BIJWERKEN
            | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
        ),
    }

    viewset_classes = {
        "enkelvoudiginformatieobject": "openzaak.components.documenten.api.viewsets.EnkelvoudigInformatieObjectViewSet",
        "zaakinformatieobject": "openzaak.components.zaken.api.viewsets.ZaakInformatieObjectViewSet",
    }

    notification_fields = {
        "enkelvoudiginformatieobject": {
            "notifications_kanaal": KANAAL_DOCUMENTEN,
            "model": EnkelvoudigInformatieObject,
        },
        "zaakinformatieobject": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": ZaakInformatieObject,
        },
    }

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        response = Response(serializer.data, status=status.HTTP_201_CREATED)

        self.create_audittrail(
            response.status_code,
            CommonResourceAction.create,
            version_before_edit=None,
            version_after_edit=serializer.data["enkelvoudiginformatieobject"],
            unique_representation=serializer.instance[
                "enkelvoudiginformatieobject"
            ].unique_representation(),
            audit=AUDIT_DRC,
            basename="enkelvoudiginformatieobject",
            main_object=serializer.data["enkelvoudiginformatieobject"]["url"],
        )

        self.create_audittrail(
            response.status_code,
            CommonResourceAction.create,
            version_before_edit=None,
            version_after_edit=serializer.data["zaakinformatieobject"],
            unique_representation=serializer.instance[
                "zaakinformatieobject"
            ].unique_representation(),
            audit=AUDIT_ZRC,
            basename="zaakinformatieobject",
            main_object=serializer.data["zaakinformatieobject"]["zaak"],
        )

        self.notify(response.status_code, response.data)
        return response

    def perform_create(self, serializer):
        data = serializer.save()
        zaak = data.get("zaakinformatieobject").zaak
        self._check_zaak_closed(zaak)

        logger.info(
            "document_geregistreerd",
            enkelvoudiginformatieobject_url=serializer.data[
                "enkelvoudiginformatieobject"
            ]["url"],
            zaak_url=serializer.data["zaakinformatieobject"]["zaak"],
        )
