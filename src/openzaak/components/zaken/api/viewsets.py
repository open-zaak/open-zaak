# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from typing import Optional

from django.db import models, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

import structlog
from django_loose_fk.virtual_models import ProxyMixin
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)
from notifications_api_common.viewsets import (
    NotificationCreateMixin,
    NotificationViewSetMixin,
)
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from vng_api_common.audittrails.viewsets import (
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    AuditTrailMixin,
    AuditTrailViewsetMixin,
)
from vng_api_common.caching import conditional_retrieve
from vng_api_common.client import to_internal_data
from vng_api_common.constants import CommonResourceAction
from vng_api_common.filters_backend import Backend
from vng_api_common.geo import GeoMixin
from vng_api_common.notes.api.viewsets import NotitieViewSetMixin
from vng_api_common.search import SearchMixin
from vng_api_common.utils import lookup_kwargs_to_filters
from vng_api_common.viewsets import CheckQueryParamsMixin, NestedViewSetMixin

from openzaak.client import get_client
from openzaak.notifications.viewsets import MultipleNotificationMixin
from openzaak.utils import get_loose_fk_object_url
from openzaak.utils.api import (
    delete_remote_objectcontactmoment,
    delete_remote_objectverzoek,
    delete_remote_oio,
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
    PRECONDITION_ERROR_RESPONSES,
    VALIDATION_ERROR_RESPONSES,
)
from openzaak.utils.views import AuditTrailViewSet

from ..models import (
    KlantContact,
    RelevanteZaakRelatie,
    Resultaat,
    Rol,
    Status,
    SubStatus,
    Zaak,
    ZaakBesluit,
    ZaakContactMoment,
    ZaakEigenschap,
    ZaakIdentificatie,
    ZaakInformatieObject,
    ZaakNotitie,
    ZaakObject,
    ZaakVerzoek,
)
from .audits import AUDIT_ZRC
from .filters import (
    KlantContactFilter,
    ResultaatFilter,
    RolFilter,
    StatusFilter,
    ZaakContactMomentFilter,
    ZaakDetailFilter,
    ZaakFilter,
    ZaakInformatieObjectFilter,
    ZaakObjectFilter,
    ZaakVerzoekFilter,
)
from .kanalen import KANAAL_ZAKEN
from .mixins import ClosedZaakMixin, UpdateOnlyModelMixin
from .permissions import (
    ZaakAuthRequired,
    ZaakNestedAuthRequired,
    ZaaKRegistrerenAuthRequired,
)
from .scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    SCOPEN_ZAKEN_HEROPENEN,
)
from .serializers import (
    GenerateZaakIdentificatieSerializer,
    KlantContactSerializer,
    ReserveZaakIdentificatieSerializer,
    ResultaatSerializer,
    RolSerializer,
    StatusSerializer,
    SubStatusSerializer,
    ZaakBesluitSerializer,
    ZaakContactMomentSerializer,
    ZaakEigenschapSerializer,
    ZaakInformatieObjectSerializer,
    ZaakNotitieSerializer,
    ZaakObjectSerializer,
    ZaakRegistrerenSerializer,
    ZaakSerializer,
    ZaakVerzoekSerializer,
    ZaakZoekSerializer,
)

logger = structlog.stdlib.get_logger(__name__)

ZAAK_UUID_PARAMETER = OpenApiParameter(
    "zaak_uuid",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Unieke resource identifier (UUID4)",
)


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKen opvragen.",
        description=(
            "Deze lijst kan gefilterd wordt met query-string parameters.\n"
            "\n"
            "**Opmerking**\n"
            "- er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd "
            "bent."
        ),
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAK opvragen.",
        description="Een specifieke ZAAK opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAK aan.",
        description=(
            "Indien geen identificatie gegeven is, dan wordt deze automatisch "
            "gegenereerd. De identificatie moet uniek zijn binnen de bronorganisatie.\n"
            "\n"
            "**Er wordt gevalideerd op**:\n"
            "- geldigheid `zaaktype` URL - de resource moet opgevraagd kunnen worden uit de "
            "Catalogi API en de vorm van een ZAAKTYPE hebben.\n"
            "- `zaaktype` is geen concept (`zaaktype.concept` = False)\n"
            "- `laatsteBetaaldatum` mag niet in de toekomst liggen.\n"
            "- `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie "
            '"nvt" is.\n'
            "- `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            "- `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            '- `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren" '
            "hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut "
            '`status` de waarde "gearchiveerd" heeft.'
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAK in zijn geheel bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- `zaaktype` mag niet gewijzigd worden.\n"
            "- `identificatie` mag niet gewijzigd worden.\n"
            "- `laatsteBetaaldatum` mag niet in de toekomst liggen.\n"
            "- `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie "
            '"nvt" is.\n'
            "- `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            "- `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            '- `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren" '
            "hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut "
            '`status` de waarde "gearchiveerd" heeft.'
            "\n"
            "**Opmerkingen**\n"
            "- er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd "
            "bent.\n"
            "- zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.\n"
            "- indien een zaak heropend moet worden, doe dit dan door een nieuwe status "
            "toe te voegen die NIET de eindstatus is. "
            "Zie de `Status` resource."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAK deels bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- `zaaktype` mag niet gewijzigd worden.\n"
            "- `identificatie` mag niet gewijzigd worden.\n"
            "- `laatsteBetaaldatum` mag niet in de toekomst liggen.\n"
            "- `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie "
            '"nvt" is.\n'
            "- `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            "- `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de "
            'waarde "nog_te_archiveren" heeft.\n'
            '- `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren" '
            "hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut "
            '`status` de waarde "gearchiveerd" heeft.'
            "\n"
            "**Opmerkingen**\n"
            "- er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd "
            "bent.\n"
            "- zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.\n"
            "- indien een zaak heropend moet worden, doe dit dan door een nieuwe status "
            "toe te voegen die NIET de eindstatus is. "
            "Zie de `Status` resource."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAK.",
        description=(
            "**De gerelateerde resources zijn hierbij**\n"
            "- `zaak` - de deelzaken van de verwijderde hoofzaak\n"
            "- `status` - alle statussen van de verwijderde zaak\n"
            "- `resultaat` - het resultaat van de verwijderde zaak\n"
            "- `rol` - alle rollen bij de zaak\n"
            "- `zaakobject` - alle zaakobjecten bij de zaak\n"
            "- `zaakeigenschap` - alle eigenschappen van de zaak\n"
            "- `zaakkenmerk` - alle kenmerken van de zaak\n"
            "- `zaakinformatieobject` - alle informatieobject van de zaak\n"
            "- `klantcontact` - alle klantcontacten bij een zaak\n"
        ),
    ),
)
@conditional_retrieve(extra_depends_on={"status"})
class ZaakViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    ExpandMixin,
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    GeoMixin,
    SearchMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKen.

    Een zaak mag (in principe) niet meer gewijzigd worden als de
    `archiefstatus` een andere status heeft dan "nog_te_archiveren". Voor
    praktische redenen is er geen harde validatie regel aan de provider kant.
    """

    queryset = (
        Zaak.objects.prefetch_related(
            # Prefetch _zaaktype instead of using `.select_related`, because using the latter
            # causes the main Zaak query to contain a lot of duplicate data, increasing overhead
            "_zaaktype",
            "deelzaken",
            models.Prefetch(
                "relevante_andere_zaken",
                queryset=RelevanteZaakRelatie.objects.select_related("_relevant_zaak"),
            ),
            "zaakkenmerk_set",
            "resultaat",
            "zaakeigenschap_set",
            models.Prefetch(
                "status_set",
                queryset=Status.objects.order_by("-datum_status_gezet"),
                # explicitly store result on this attribute, that way we can retrieve
                # the first status by simple list indexing, which is faster than calling
                # `.first()`, because the latter instantiates a new queryset
                to_attr="prefetched_statuses",
            ),
            "rol_set",
            "zaakinformatieobject_set",
            "zaakobject_set",
        )
        .order_by("-pk")
        .distinct()
    )
    serializer_class = ZaakSerializer
    search_input_serializer_class = ZaakZoekSerializer
    filter_backends = (Backend,)
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "_zoek": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC
    _generated_identificatie: Optional[ZaakIdentificatie] = None

    def get_queryset(self):
        qs = super().get_queryset()
        # codepath via the the `get_viewset_for_path` utilities in various libraries
        # does not always initialize a request, which causes self.action to not be set.
        # FIXME: extract that utility into a separate library to unify it
        action = getattr(self, "action", None)
        if action not in ["list", "_zoek"]:
            # ⚡️ drop the prefetches when only selecting a single record. If the data
            # is needed, the queries will be done during serialization and the amount
            # of queries will be the same.
            qs = qs.prefetch_related(None)

        if action not in ["list", "detail", "_zoek"]:
            # Catalogus is only relevant for notifications (to include the `zaaktype.catalogus`)
            # kenmerk. The read operations are slightly slower if we include this `select_related`
            # on the base queryset, because it adds an extra join
            qs = qs.select_related("_zaaktype__catalogus")

        return qs

    @property
    def filterset_class(self):
        """
        support expand in the detail endpoint
        """
        if self.detail:
            return ZaakDetailFilter
        return ZaakFilter

    @extend_schema(
        "zaak__zoek",
        summary="Voer een (geo)-zoekopdracht uit op ZAAKen.",
        description=(
            "Zoeken/filteren gaat normaal via de `list` operatie, deze is echter "
            "niet geschikt voor geo-zoekopdrachten."
        ),
        responses={
            status.HTTP_200_OK: ZaakSerializer(many=True),
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
            **PRECONDITION_ERROR_RESPONSES,
        },
    )
    @action(methods=("post",), detail=False, name="zaak__zoek")
    def _zoek(self, request, *args, **kwargs):
        if not request.data:
            err = serializers.ErrorDetail(
                _("Search parameters must be specified"), code="empty_search_body"
            )
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY: err})

        search_input = self.get_search_input()
        queryset = self.filter_queryset(self.get_queryset())

        for name, value in search_input.items():
            if name == "zaakgeometrie":
                queryset = queryset.filter(zaakgeometrie__within=value["within"])
            else:
                queryset = queryset.filter(**{name: value})

        return self.get_search_output(queryset)

    _zoek.is_search_action = True

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return {
            **context,
            "generated_identificatie": self._generated_identificatie,
        }

    def create(self, request, *args, **kwargs):
        # Override the parent create to generate an identification _if needed_. The
        # super create call runs in its own transaction (from NotificationViewSetMixin)
        # and if needed, we run the identification generation in a separate DB
        # transaction to mitigate race conditions.

        if not request.data.get("identificatie") and request.data.get(
            "bronorganisatie"
        ):
            self._generate_zaakidentificatie(request.data)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        zaak = serializer.instance
        logger.info(
            "zaak_created",
            uuid=str(zaak.uuid),
            identificatie=zaak.identificatie,
            vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            zaaktype=str(zaak.zaaktype),
        )

    @transaction.atomic()
    def _generate_zaakidentificatie(self, data: dict):
        serializer = GenerateZaakIdentificatieSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        self._generated_identificatie = serializer.save()

    def perform_update(self, serializer):
        """
        Perform the update of the Case.

        After input validation and before DB persistance we need to check
        scope-related permissions. Only SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN scope
        allows to alter closed cases

        :raises: PermissionDenied if attempting to alter a closed case with
        insufficient permissions

        """
        zaak = self.get_object()
        zaak_data = self.get_serializer(zaak).data

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=self.queryset.model._meta.app_label,
        ):
            if zaak.is_closed:
                msg = "Modifying a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)
        super().perform_update(serializer)

        updated_zaak = serializer.instance

        logger.info(
            "zaak_updated",
            uuid=str(updated_zaak.uuid),
            identificatie=updated_zaak.identificatie,
            vertrouwelijkheidaanduiding=updated_zaak.vertrouwelijkheidaanduiding,
            zaaktype=str(updated_zaak.zaaktype),
            partial=serializer.partial,
        )

    def perform_destroy(self, instance: Zaak):
        if instance.besluit_set.exists():
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "Zaak has related Besluit(en), these relations should be deleted "
                        "before deleting the Zaak"
                    )
                },
                code="related-besluiten",
            )

        # check if we need to delete any remote OIOs
        autocommit = transaction.get_autocommit()
        assert autocommit is False, "Expected to be in a transaction.atomic block"
        # evaluate the queryset, because the transaction will delete the records with
        # a cascade
        # In the CMIS case, _informatieobject is None, but the _objectinformatieobject_url is not set
        # (internal document behaviour)
        oio_urls = instance.zaakinformatieobject_set.filter(
            Q(_informatieobject__isnull=True), ~Q(_objectinformatieobject_url="")
        ).values_list("_objectinformatieobject_url", flat=True)
        delete_params = [
            (url, get_client(url, raise_exceptions=True)) for url in oio_urls
        ]

        def _delete_oios():
            for url, client in delete_params:
                to_internal_data(client.delete(url))

        transaction.on_commit(_delete_oios)

        super().perform_destroy(instance)

        logger.info(
            "zaak_deleted",
            uuid=str(instance.uuid),
            identificatie=instance.identificatie,
            vertrouwelijkheidaanduiding=instance.vertrouwelijkheidaanduiding,
            zaaktype=str(instance.zaaktype),
        )

    def get_search_input(self):
        serializer = self.get_search_input_serializer_class()(
            data=self.request.data, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


@extend_schema_view(
    list=extend_schema(
        summary="Alle STATUSsen van ZAAKen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke STATUS van een ZAAK opvragen.",
        description="Een specifieke STATUS van een ZAAK opvragen.",
    ),
    create=extend_schema(
        summary="Maak een STATUS aan voor een ZAAK.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK\n"
            "- geldigheid URL naar het STATUSTYPE\n"
            "- indien het de eindstatus betreft, dan moet het attribuut "
            "`indicatieGebruiksrecht` gezet zijn op alle informatieobjecten die aan "
            "de zaak gerelateerd zijn\n"
            "- indien de zaak deelzaken heeft moeten de deelzaken gesloten zijn voordat de hoofdzaak kan "
            "worden afgesloten met de eindstatus\n"
            "- indien een zaak wordt heropend en een hoofdzaak heeft, dan mag de hoofdzaak niet gesloten zijn\n"
            "\n"
            "**Opmerkingen**\n"
            "- Indien het statustype de eindstatus is (volgens het ZTC), dan wordt de "
            "zaak afgesloten door de einddatum te zetten.\n"
            "- Bij deelzaken met een `Resultaat.resultaattype.brondatumArchiefprocedure.afleidingswijze` `hoofdzaak` "
            "word de brondatum van de hoofdzaak ingevuld nadat de hoofdzaak is afgesloten."
        ),
    ),
)
@conditional_retrieve()
class StatusViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en beheren van zaakstatussen.
    """

    queryset = (
        Status.objects.select_related("_statustype", "zaak", "gezetdoor")
        .prefetch_related("zaakinformatieobjecten")
        .annotate_with_max_datum_status_gezet()
        .order_by("-datum_status_gezet", "-pk")
    )
    serializer_class = StatusSerializer
    filterset_class = StatusFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE
        | SCOPE_STATUSSEN_TOEVOEGEN
        | SCOPEN_ZAKEN_HEROPENEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def perform_create(self, serializer):
        """
        Perform the create of the Status.

        After input validation and before DB persistance we need to check
        scope-related permissions. Three scopes are allowed to create new
        Status objects:
        - create initial status
        - create initial status and subsequent statuses until the case is closed
        - create any status before or after the case is closed

        :raises: PermissionDenied if attempting to create another Status with
          insufficient permissions
        """
        zaak = serializer.validated_data["zaak"]
        zaak_data = ZaakSerializer(zaak, context={"request": self.request}).data
        component = self.queryset.model._meta.app_label

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_STATUSSEN_TOEVOEGEN | SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=component,
        ):
            if zaak.status_set.exists():
                msg = f"Met de '{SCOPE_ZAKEN_CREATE}' scope mag je slechts 1 status zetten"
                raise PermissionDenied(detail=msg)

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=component,
        ):
            if zaak.is_closed:
                msg = "Reopening a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)

        super().perform_create(serializer)
        status_obj = serializer.instance
        logger.info(
            "status_created",
            uuid=str(status_obj.uuid),
            zaak_uuid=str(status_obj.zaak.uuid) if status_obj.zaak else None,
            statustype=str(status_obj.statustype)
            if hasattr(status_obj, "statustype")
            else None,
            gezetdoor=str(status_obj.gezetdoor) if status_obj.gezetdoor else None,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle SUBSTATUSsen van STATUSsen opvragen.",
        description=mark_experimental(
            "Deze lijst kan gefilterd wordt met query-string parameters."
        ),
    ),
    retrieve=extend_schema(
        summary="Een specifieke SUBSTATUS bij een STATUS van een ZAAK opvragen.",
        description=mark_experimental(
            "Een specifieke SUBSTATUS bij een STATUS van een ZAAK opvragen."
        ),
    ),
    create=extend_schema(
        summary="Maak een SUBSTATUS aan bij een STATUS voor een ZAAK.",
        description=mark_experimental(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK\n"
            "- geldigheid URL naar de STATUS\n"
            "- STATUS moet horen bij de ZAAK"
        ),
    ),
)
class SubStatusViewSet(
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en beheren van substatussen.
    list:
    Alle SUBSTATUSsen van STATUSsen opvragen.
    Deze lijst kan gefilterd wordt met query-string parameters.
    retrieve:
    Een specifieke SUBSTATUS bij een STATUS van een ZAAK opvragen.
    Een specifieke SUBSTATUS bij een STATUS van een ZAAK opvragen.
    create:
    Maak een SUBSTATUS aan bij een STATUS voor een ZAAK.
    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - geldigheid URL naar de STATUS
    - STATUS moet horen bij de ZAAK
    """

    queryset = SubStatus.objects.select_related("zaak", "status").order_by("-tijdstip")
    serializer_class = SubStatusSerializer
    filterset_fields = {
        "zaak": ["exact"],
        "doelgroep": ["exact"],
        "status": ["exact"],
        "tijdstip": ["gt", "lt", "gte", "lte"],
    }
    lookup_field = "uuid"
    pagination_class = PageNumberPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE | SCOPE_STATUSSEN_TOEVOEGEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKOBJECTen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifiek ZAAKOBJECT opvragen.",
        description="Een specifiek ZAAKOBJECT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKOBJECT aan.",
        description=(
            "Maak een ZAAKOBJECT aan.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "\n"
            "- Indien de `object` URL opgegeven is, dan moet deze een geldige response "
            "(HTTP 200) geven.\n"
            "- Indien opgegeven, dan wordt `objectIdentificatie` gevalideerd tegen de "
            "`objectType` discriminator."
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAKOBJECT in zijn geheel bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "\n"
            "- De attributen `zaak`, `object` en `objectType` mogen niet gewijzigd worden.\n"
            "- Indien opgegeven, dan wordt `objectIdentificatie` gevalideerd tegen de "
            "`objectType` discriminator."
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKOBJECT deels bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "\n"
            "- De attributen `zaak`, `object` en `objectType` mogen niet gewijzigd worden.\n"
            "- Indien opgegeven, dan wordt `objectIdentificatie` gevalideerd tegen de "
            "`objectType` discriminator."
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKOBJECT.",
        description=(
            "Verbreek de relatie tussen een ZAAK en een OBJECT door de ZAAKOBJECT resource te "
            "verwijderen."
        ),
    ),
)
class ZaakObjectViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    CheckQueryParamsMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    ClosedZaakMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKOBJECTen.
    """

    queryset = ZaakObject.objects.select_related("zaak", "_zaakobjecttype").order_by(
        "-pk"
    )
    serializer_class = ZaakObjectSerializer
    filterset_class = ZaakObjectFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE
        | SCOPE_ZAKEN_BIJWERKEN
        | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN
        | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
        | SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        logger.info(
            "zaakobject_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid) if instance.zaak else None,
            object_url=str(getattr(instance, "object", None)),
            object_type=str(instance.object_type),
            client_id=self.request.jwt_auth.client_id,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "zaakobject_updated",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid) if instance.zaak else None,
            client_id=self.request.jwt_auth.client_id,
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid) if instance.zaak else None

        super().perform_destroy(instance)

        logger.info(
            "zaakobject_deleted",
            uuid=uuid,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAK-INFORMATIEOBJECT relaties opvragen.",
        description="Deze lijst kan gefilterd wordt met querystringparameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.",
        description="Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAK-INFORMATIEOBJECT relatie aan.",
        description=(
            "Er worden twee types van relaties met andere objecten gerealiseerd:\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- geldigheid zaak URL\n"
            "- geldigheid informatieobject URL\n"
            "- de combinatie informatieobject en zaak moet uniek zijn\n"
            "\n"
            "**Opmerkingen**\n"
            "- De registratiedatum wordt door het systeem op 'NU' gezet. De `aardRelatie` "
            "wordt ook door het systeem gezet.\n"
            "- Bij het aanmaken wordt ook in de Documenten API de gespiegelde relatie aangemaakt, "
            "echter zonder de relatie-informatie.\n"
            "\n"
            "Registreer welk(e) INFORMATIEOBJECT(en) een ZAAK kent.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- geldigheid informatieobject URL\n"
            "- uniek zijn van relatie ZAAK-INFORMATIEOBJECT"
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAK-INFORMATIEOBJECT relatie in zijn geheel bij.",
        description=(
            "Je mag enkel de gegevens "
            "van de relatie bewerken, en niet de relatie zelf aanpassen.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- informatieobject URL en zaak URL mogen niet veranderen"
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAK-INFORMATIEOBJECT relatie in deels bij.",
        description=(
            "Je mag enkel de gegevens "
            "van de relatie bewerken, en niet de relatie zelf aanpassen.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- informatieobject URL en zaak URL mogen niet veranderen"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAK-INFORMATIEOBJECT relatie.",
        description=(
            "De gespiegelde relatie in de Documenten API wordt door de Zaken API "
            "verwijderd. Consumers kunnen dit niet handmatig doen."
        ),
    ),
)
@conditional_retrieve()
class ZaakInformatieObjectViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    AuditTrailViewsetMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    ClosedZaakMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAK-INFORMATIEOBJECT relaties.
    """

    queryset = (
        ZaakInformatieObject.objects.select_related("zaak", "_informatieobject")
        .prefetch_related("_informatieobject__enkelvoudiginformatieobject_set")
        .order_by("-pk")
    )
    filterset_class = ZaakInformatieObjectFilter
    serializer_class = ZaakInformatieObjectSerializer
    lookup_field = "uuid"
    notifications_kanaal = KANAAL_ZAKEN
    notifications_main_resource_key = "zaak"
    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_CREATE
        | SCOPE_ZAKEN_BIJWERKEN
        | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN
        | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
        | SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    audit = AUDIT_ZRC

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
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "zaakinformatieobject_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)

        instance = serializer.instance

        logger.info(
            "zaakinformatieobject_updated",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
            partial=serializer.partial,
        )

    def perform_destroy(self, instance: ZaakInformatieObject):
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid)

        with transaction.atomic():
            super().perform_destroy(instance)

        if (
            isinstance(instance.informatieobject, ProxyMixin)
            and instance._objectinformatieobject_url
        ):
            try:
                delete_remote_oio(instance._objectinformatieobject_url)
            except Exception as exception:
                # bring back the instance
                instance.save()
                raise ValidationError(
                    {
                        "informatieobject": _(
                            "Could not delete remote relation: {exc}"
                        ).format(exc=exception)
                    },
                    code="pending-relations",
                )

        logger.info(
            "zaakinformatieobject_deleted",
            uuid=uuid,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )


@extend_schema(parameters=[ZAAK_UUID_PARAMETER])
@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKEIGENSCHAPpen opvragen.",
        description="Alle ZAAKEIGENSCHAPpen opvragen.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAKEIGENSCHAP opvragen.",
        description="Een specifieke ZAAKEIGENSCHAP opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKEIGENSCHAP aan.",
        description=(
            "Maak een ZAAKEIGENSCHAP aan.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "\n"
            "- **EXPERIMENTEEL** `waarde` moet worden gevalideerd tegen "
            "`eigenschap.specificatie` indien `ZAAK_EIGENSCHAP_WAARDE_VALIDATION` "
            "op `True` staat."
        ),
    ),
    update=extend_schema(
        summary="Werk een ZAAKEIGENSCHAP in zijn geheel bij.",
        description=(
            "**Er wordt gevalideerd op**\n\n- Alleen de WAARDE mag gewijzigd worden"
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKEIGENSCHAP deels bij.",
        description=(
            "**Er wordt gevalideerd op**\n\n- Alleen de WAARDE mag gewijzigd worden"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKEIGENSCHAP.",
        description="Verwijder een ZAAKEIGENSCHAP.",
    ),
)
@conditional_retrieve()
class ZaakEigenschapViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationViewSetMixin,
    AuditTrailCreateMixin,
    NestedViewSetMixin,
    ClosedZaakMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKEIGENSCHAPpen
    """

    queryset = ZaakEigenschap.objects.select_related("zaak", "_eigenschap").order_by(
        "-pk"
    )
    serializer_class = ZaakEigenschapSerializer
    permission_classes = (ZaakNestedAuthRequired,)
    lookup_field = "uuid"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    }
    parent_retrieve_kwargs = {"zaak_uuid": "uuid"}
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def get_queryset(self):
        if not self.kwargs:  # this happens during schema generation, and causes crashes
            return self.queryset.none()
        return super().get_queryset()

    def _get_zaak(self):
        if not hasattr(self, "_zaak"):
            filters = lookup_kwargs_to_filters(self.parent_retrieve_kwargs, self.kwargs)
            self._zaak = get_object_or_404(Zaak, **filters)
        return self._zaak

    def initialize_request(self, request, *args, **kwargs):
        # workaround for drf-nested-viewset injecting the URL kwarg into request.data
        return super(viewsets.ModelViewSet, self).initialize_request(
            request, *args, **kwargs
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "zaakeigenschap_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)

        instance = serializer.instance

        logger.info(
            "zaakeigenschap_updated",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid)

        super().perform_destroy(instance)

        logger.info(
            "zaakeigenschap_deleted",
            uuid=uuid,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )


# XXX: remove in 2.0
@extend_schema_view(
    list=extend_schema(
        summary="Alle KLANTCONTACTen opvragen.",
        description=(
            "Alle KLANTCONTACTen opvragen.\n"
            "\n"
            "**DEPRECATED**: gebruik de contactmomenten API in plaats van deze endpoint."
        ),
        deprecated=True,
    ),
    retrieve=extend_schema(
        summary="Een specifiek KLANTCONTACT bij een ZAAK opvragen.",
        description=(
            "Een specifiek KLANTCONTACT bij een ZAAK opvragen.\n"
            "\n"
            "**DEPRECATED**: gebruik de contactmomenten API in plaats van deze endpoint."
        ),
        deprecated=True,
    ),
    create=extend_schema(
        summary="Maak een KLANTCONTACT bij een ZAAK aan.",
        description=(
            "Indien geen identificatie gegeven is, dan wordt deze automatisch "
            "gegenereerd.\n"
            "\n"
            "**DEPRECATED**: gebruik de contactmomenten API in plaats van deze endpoint."
        ),
        deprecated=True,
    ),
)
class KlantContactViewSet(
    CheckQueryParamsMixin,
    NotificationCreateMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailCreateMixin,
    ClosedZaakMixin,
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van KLANTCONTACTen.
    """

    queryset = KlantContact.objects.select_related("zaak").order_by("-pk")
    serializer_class = KlantContactSerializer
    filterset_class = KlantContactFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    deprecation_message = (
        "Deze endpoint is verouderd en zal binnenkort uit dienst worden genomen. "
        "Maak gebruik van de vervangende contactmomenten API."
    )

    def perform_create(self, serializer):
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "klantcontact_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle ROLlen bij ZAAKen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke ROL bij een ZAAK opvragen.",
        description="Een specifieke ROL bij een ZAAK opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ROL aan bij een ZAAK.",
        description=(
            "Maak een ROL aan bij een ZAAK.\n\n"
            "BetrokkeneType `vestiging` is **DEPRECATED**."
        ),
    ),
    update=extend_schema(
        summary="Werk een ROL aan bij een ZAAK.",
        description=mark_experimental("Werk een ROL aan bij een ZAAK."),
    ),
    destroy=extend_schema(
        summary="Verwijder een ROL van een ZAAK.",
        description="Verwijder een ROL van een ZAAK.",
    ),
)
@conditional_retrieve()
class RolViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    ClosedZaakMixin,
    mixins.CreateModelMixin,
    UpdateOnlyModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ROL relatie tussen een ZAAK en een BETROKKENE.
    """

    queryset = (
        Rol.objects.select_related("_roltype", "zaak")
        .prefetch_related(
            "natuurlijkpersoon",
            "nietnatuurlijkpersoon",
            "vestiging",
            "organisatorischeeenheid",
            "medewerker",
            "statussen",
        )
        .order_by("-pk")
    )
    serializer_class = RolSerializer
    filterset_class = RolFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def perform_create(self, serializer):
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "rol_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)

        instance = serializer.instance

        logger.info(
            "rol_updated",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid)

        super().perform_destroy(instance)

        logger.info(
            "rol_deleted",
            uuid=uuid,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle RESULTAATen van ZAAKen opvragen.",
        description="Deze lijst kan gefilterd wordt met query-string parameters.",
    ),
    retrieve=extend_schema(
        summary="Een specifiek RESULTAAT opvragen.",
        description="Een specifiek RESULTAAT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een RESULTAAT bij een ZAAK aan.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK\n"
            "- geldigheid URL naar het RESULTAATTYPE\n"
        ),
    ),
    update=extend_schema(
        summary="Werk een RESULTAAT in zijn geheel bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK\n"
            "- het RESULTAATTYPE mag niet gewijzigd worden"
        ),
    ),
    partial_update=extend_schema(
        summary="Werk een RESULTAAT deels bij.",
        description=(
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK\n"
            "- het RESULTAATTYPE mag niet gewijzigd worden"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een RESULTAAT van een ZAAK.",
        description="Verwijder een RESULTAAT van een ZAAK.",
    ),
)
@conditional_retrieve()
class ResultaatViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationViewSetMixin,
    AuditTrailViewsetMixin,
    CheckQueryParamsMixin,
    ListFilterByAuthorizationsMixin,
    ClosedZaakMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en beheren van resultaten.
    """

    queryset = Resultaat.objects.select_related("_resultaattype", "zaak").order_by(
        "-pk"
    )
    serializer_class = ResultaatSerializer
    filterset_class = ResultaatFilter
    lookup_field = "uuid"
    pagination_class = OptimizedPagination

    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        "partial_update": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def perform_create(self, serializer):
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "resultaat_created",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)

        instance = serializer.instance

        logger.info(
            "resultaat_updated",
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
            client_id=self.request.jwt_auth.client_id,
            partial=serializer.partial,
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid)

        super().perform_destroy(instance)

        logger.info(
            "resultaat_deleted",
            uuid=uuid,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )


@extend_schema(parameters=[ZAAK_UUID_PARAMETER])
@extend_schema_view(
    list=extend_schema(
        summary="Alle audit trail regels behorend bij de ZAAK.",
        description="Alle audit trail regels behorend bij de ZAAK.",
    ),
    retrieve=extend_schema(
        summary="Een specifieke audit trail regel opvragen.",
        description="Een specifieke audit trail regel opvragen.",
    ),
)
class ZaakAuditTrailViewSet(AuditTrailViewSet):
    """
    Opvragen van Audit trails horend bij een ZAAK.
    """

    main_resource_lookup_field = "zaak_uuid"
    permission_classes = (AuthRequired,)


@extend_schema(parameters=[ZAAK_UUID_PARAMETER])
@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKBESLUITen opvragen.",
        description="Alle ZAAKBESLUITen opvragen.",
    ),
    retrieve=extend_schema(
        summary="Een specifiek ZAAKBESLUIT opvragen.",
        description="Een specifiek ZAAKBESLUIT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKBESLUIT aan.",
        description=(
            "**LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**\n"
            "\n"
            "De Besluiten API gebruikt dit endpoint om relaties te synchroniseren, "
            "daarom is dit endpoint in de Zaken API geimplementeerd.\n"
            "\n"
            "**Er wordt gevalideerd op**\n"
            "- geldigheid URL naar de ZAAK"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKBESLUIT.",
        description=(
            "**LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**\n"
            "\n"
            "De Besluiten API gebruikt dit endpoint om relaties te synchroniseren, "
            "daarom is dit endpoint in de Zaken API geimplementeerd."
        ),
    ),
)
class ZaakBesluitViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    NestedViewSetMixin,
    ClosedZaakMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en beheren van zaak-besluiten.
    """

    queryset = ZaakBesluit.objects.order_by("-pk")
    serializer_class = ZaakBesluitSerializer
    lookup_field = "uuid"
    parent_retrieve_kwargs = {"zaak_uuid": "uuid"}
    permission_classes = (ZaakNestedAuthRequired,)
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def get_queryset(self):
        if not self.kwargs:  # this happens during schema generation, and causes crashes
            return self.queryset.none()
        return super().get_queryset()

    def _get_zaak(self):
        if not hasattr(self, "_zaak"):
            self._zaak = get_object_or_404(Zaak, uuid=self.kwargs["zaak_uuid"])
        return self._zaak

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # DRF introspection
        if not self.kwargs:
            return context

        context["parent_object"] = self._get_zaak()
        return context

    def perform_create(self, serializer):
        """
        Handle the creation logic.
        """
        besluit = serializer.validated_data["besluit"]
        besluit_url = get_loose_fk_object_url(besluit, self.request)

        # external besluit
        if isinstance(besluit, ProxyMixin):
            super().perform_create(serializer)
            logger.info(
                "zaakbesluit_created_external",
                besluit_url=besluit_url,
                zaak_uuid=self.kwargs["zaak_uuid"],
                client_id=self.request.jwt_auth.client_id,
            )
            return

        # for local besluit nothing extra happens here, since the creation is entirely managed via
        # the Besluit resource. We just perform some extra sanity checks in the
        # serializer.
        try:
            serializer.instance = self.get_queryset().get(
                besluit=besluit,
                zaak=self._get_zaak(),
            )
            logger.info(
                "zaakbesluit_relation_exists",
                besluit_url=besluit_url,
                zaak_uuid=self.kwargs["zaak_uuid"],
                client_id=self.request.jwt_auth.client_id,
            )
        except ZaakBesluit.DoesNotExist:
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The relation between zaak and besluit doesn't exist"
                    )
                },
                code="inconsistent-relation",
            )

    def get_audittrail_main_object_url(self, data, main_resource) -> str:
        return reverse(
            "zaak-detail",
            request=self.request,
            kwargs={"uuid": self.kwargs["zaak_uuid"]},
        )

    def get_notification_main_object_url(self, data, kanaal):
        return reverse(
            "zaak-detail",
            request=self.request,
            kwargs={"uuid": self.kwargs["zaak_uuid"]},
        )

    def perform_destroy(self, instance: ZaakBesluit):
        """
        'Delete' the relation between zaak & besluit.
        """
        uuid = str(instance.uuid)
        zaak_uuid = str(instance.zaak.uuid)
        besluit_url = get_loose_fk_object_url(instance.besluit, self.request)
        # external besluit
        if isinstance(instance.besluit, ProxyMixin):
            super().perform_destroy(instance)
            logger.info(
                "zaakbesluit_deleted_external",
                uuid=uuid,
                besluit_url=besluit_url,
                zaak_uuid=zaak_uuid,
                client_id=self.request.jwt_auth.client_id,
            )
            return

        # for local besluit the actual relation information must be updated in the Besluiten API,
        # so this is just a check.
        if instance.besluit.zaak == instance.zaak:
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "Het Besluit verwijst nog naar deze zaak. "
                        "Deze relatie moet eerst verbroken worden."
                    )
                },
                code="inconsistent-relation",
            )

        logger.info(
            "zaakbesluit_relation_deleted",
            uuid=uuid,
            besluit_url=besluit_url,
            zaak_uuid=zaak_uuid,
            client_id=self.request.jwt_auth.client_id,
        )
        super().perform_destroy(instance)

    def initialize_request(self, request, *args, **kwargs):
        # workaround for drf-nested-viewset injecting the URL kwarg into request.data
        return super(viewsets.GenericViewSet, self).initialize_request(
            request, *args, **kwargs
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKCONTACTMOMENTen opvragen.",
        description="Alle ZAAKCONTACTMOMENTen opvragen.",
    ),
    retrieve=extend_schema(
        summary="Een specifiek ZAAKCONTACTMOMENT opvragen.",
        description="Een specifiek ZAAKCONTACTMOMENT opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAKCONTACTMOMENT aan.",
        description=(
            "**Er wordt gevalideerd op**\n- geldigheid URL naar de CONTACTMOMENT"
        ),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKCONTACTMOMENT.",
        description="Verwijder een ZAAKCONTACTMOMENT.",
    ),
)
class ZaakContactMomentViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    ListFilterByAuthorizationsMixin,
    CheckQueryParamsMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ZAAK-CONTACTMOMENT relaties.
    """

    queryset = ZaakContactMoment.objects.order_by("-pk")
    serializer_class = ZaakContactMomentSerializer
    filterset_class = ZaakContactMomentFilter
    lookup_field = "uuid"
    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

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
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "zaakcontactmoment_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
            zaak_uuid=str(instance.zaak.uuid),
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        with transaction.atomic():
            super().perform_destroy(instance)

        if instance._objectcontactmoment:
            try:
                delete_remote_objectcontactmoment(instance._objectcontactmoment)
            except Exception as exception:
                # bring back the instance
                instance.save()
                raise ValidationError(
                    {
                        "contactmoment": _(
                            "Could not delete remote relation: {exc}"
                        ).format(exc=exception)
                    },
                    code="pending-relations",
                )

        logger.info(
            "zaakcontactmoment_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAK-VERZOEK opvragen.", description="Alle ZAAK-VERZOEK opvragen."
    ),
    retrieve=extend_schema(
        summary="Een specifiek ZAAK-VERZOEK opvragen.",
        description="Een specifiek ZAAK-VERZOEK opvragen.",
    ),
    create=extend_schema(
        summary="Maak een ZAAK-VERZOEK aan.",
        description=("**Er wordt gevalideerd op**\n- geldigheid URL naar de VERZOEK"),
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAK-VERZOEK.", description="Verwijder een ZAAK-VERZOEK."
    ),
)
class ZaakVerzoekViewSet(
    CacheQuerysetMixin,  # should be applied before other mixins
    NotificationCreateMixin,
    AuditTrailCreateMixin,
    AuditTrailDestroyMixin,
    ListFilterByAuthorizationsMixin,
    CheckQueryParamsMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ZAAK-VERZOEK relaties.
    """

    queryset = ZaakVerzoek.objects.order_by("-pk")
    serializer_class = ZaakVerzoekSerializer
    filterset_class = ZaakVerzoekFilter
    lookup_field = "uuid"
    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "zaak"
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

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
        super().perform_create(serializer)

        instance = serializer.instance

        logger.info(
            "zaakverzoek_created",
            client_id=self.request.jwt_auth.client_id,
            uuid=str(instance.uuid),
        )

    def perform_destroy(self, instance):
        uuid = str(instance.uuid)
        with transaction.atomic():
            super().perform_destroy(instance)

        if instance._objectverzoek:
            try:
                delete_remote_objectverzoek(instance._objectverzoek)
            except Exception as exception:
                instance.save()  # revert deletion
                raise ValidationError(
                    {
                        "verzoek": _("Could not delete remote relation: {exc}").format(
                            exc=exception
                        )
                    },
                    code="pending-relations",
                )

        logger.info(
            "zaakverzoek_deleted",
            client_id=self.request.jwt_auth.client_id,
            uuid=uuid,
        )


@extend_schema_view(
    create=extend_schema(
        operation_id="zaaknummer_reserveren",
        summary="Reserveer een zaaknummer",
        description=mark_experimental(
            "Reserveer een zaaknummer binnen een specifieke bronorganisatie zonder direct een Zaak aan te maken. "
            "Dit zaaknummer zal toegekend worden aan de eerstvolgende Zaak die met dit zaaknummer wordt aangemaakt "
            "binnen de bronorganisatie en het zaaknummer kan daarna niet hergebruikt worden.\n\n"
            "Als `aantal` niet wordt opgegeven of gelijk is aan 1, wordt een enkel object teruggegeven.\n"
            "Als `aantal > 1`, wordt een lijst van objecten teruggegeven."
        ),
        request=ReserveZaakIdentificatieSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                response=PolymorphicProxySerializer(
                    component_name="OneOrMultipleZaakIdentificaties",
                    serializers=[
                        ReserveZaakIdentificatieSerializer,
                        ReserveZaakIdentificatieSerializer(many=True),
                    ],
                    resource_type_field_name=None,
                    many=False,
                )
            ),
            **VALIDATION_ERROR_RESPONSES,
            **COMMON_ERROR_RESPONSES,
            **PRECONDITION_ERROR_RESPONSES,
        },
        examples=[
            OpenApiExample(
                "Enkele reservering",
                value={"zaaknummer": "ZAAK-2025-0000000001"},
                response_only=True,
            ),
            OpenApiExample(
                "Meerdere reserveringen",
                value=[
                    {"zaaknummer": "ZAAK-2025-0000000001"},
                    {"zaaknummer": "ZAAK-2025-0000000002"},
                ],
                response_only=True,
            ),
        ],
    )
)
class ReserveerZaakNummerViewSet(viewsets.ViewSet):
    """
    Reserveer een zaaknummer.
    """

    queryset = ZaakIdentificatie.objects.order_by("-pk")
    serializer_class = ReserveZaakIdentificatieSerializer
    permission_classes = (AuthRequired,)
    required_scopes = {
        "create": SCOPE_ZAKEN_CREATE,
    }

    def create(self, request, *args, **kwargs):
        serializer = ReserveZaakIdentificatieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        if isinstance(result, list):
            response_data = ReserveZaakIdentificatieSerializer(result, many=True).data
        else:
            response_data = ReserveZaakIdentificatieSerializer(result).data

        logger.info(
            "zaaknummer_gereserveerd",
            client_id=request.jwt_auth.client_id,
            path=request.get_full_path(),
            method=request.method,
            input_data=request.data,
            response_data=response_data,
            count=len(response_data) if isinstance(response_data, list) else 1,
        )

        return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    create=extend_schema(
        operation_id="zaak_reserveer_zaaknummer",
        deprecated=True,
        description=mark_experimental(
            "LET OP: dit endpoint is verouderd en zal in de toekomst verwijderd worden, "
            "gebruik in plaats van dit endpoint `/zaaknummer_reserveren`\n\n"
            "Reserveer een zaaknummer binnen een specifieke bronorganisatie zonder direct een Zaak aan te maken. "
            "Dit zaaknummer zal toegekend worden aan de eerstvolgende Zaak die met dit zaaknummer wordt aangemaakt "
            "binnen de bronorganisatie en het zaaknummer kan daarna niet hergebruikt worden.\n\n"
            "Als `aantal` niet wordt opgegeven of gelijk is aan 1, wordt een enkel object teruggegeven.\n"
            "Als `aantal > 1`, wordt een lijst van objecten teruggegeven."
        ),
    )
)
class DeprecatedReserveerZaakNummerViewSet(ReserveerZaakNummerViewSet):
    deprecation_message = (
        "This endpoint is an alias for `/zaaknummer_reserveren` and will be removed in "
        "the next major version. Please use `/zaaknummer_reserveren` instead."
    )


@extend_schema_view(
    list=extend_schema(
        summary="Alle ZAAKNOTITIEs opvragen.",
        description=mark_experimental("Alle ZAAKNOTITIEs opvragen."),
    ),
    retrieve=extend_schema(
        summary="Een specifieke ZAAKNOTITIE opvragen.",
        description=mark_experimental("Een specifieke ZAAKNOTITIE opvragen."),
    ),
    create=extend_schema(
        summary="Maak een ZAAKNOTITIE aan.",
        description=mark_experimental("Maak een ZAAKNOTITIE aan."),
    ),
    update=extend_schema(
        summary="Werk een ZAAKNOTITIE in zijn geheel bij.",
        description=mark_experimental("Werk een ZAAKNOTITIE in zijn geheel bij.")
        + "\n\n **WARNING**: Notitie can only be modified when status is `concept`",
    ),
    partial_update=extend_schema(
        summary="Werk een ZAAKNOTITIE deels bij.",
        description=mark_experimental("Werk een ZAAKNOTITIE deels bij.")
        + "\n\n **WARNING**: Notitie can only be modified when status is `concept`",
    ),
    destroy=extend_schema(
        summary="Verwijder een ZAAKNOTITIE.",
        description=mark_experimental("Verwijder een ZAAKNOTITIE."),
    ),
)
class ZaakNotitieViewSet(
    NotitieViewSetMixin, ListFilterByAuthorizationsMixin, viewsets.ModelViewSet
):
    queryset = ZaakNotitie.objects.select_related("gerelateerd_aan").order_by("-pk")

    serializer_class = ZaakNotitieSerializer
    lookup_field = "uuid"
    pagination_class = OptimizedPagination
    permission_classes = (ZaakAuthRequired,)
    permission_main_object = "gerelateerd_aan"  # zaak
    required_scopes = {
        "list": SCOPE_ZAKEN_ALLES_LEZEN,
        "retrieve": SCOPE_ZAKEN_ALLES_LEZEN,
        "create": SCOPE_ZAKEN_BIJWERKEN,
        "update": SCOPE_ZAKEN_BIJWERKEN,
        "destroy": SCOPE_ZAKEN_BIJWERKEN,
    }


@extend_schema(
    summary="Registreer een zaak",
    description=mark_experimental(
        "Maak een Zaak samen met een status, rollen, zaakinformatieobjecten en zaakobjecten aan om alles direct aan de zaak te linken."
    ),
)
class ZaakRegistrerenViewset(
    viewsets.ViewSet, MultipleNotificationMixin, AuditTrailMixin, GeoMixin
):
    serializer_class = ZaakRegistrerenSerializer
    permission_classes = (ZaaKRegistrerenAuthRequired,)
    required_scopes = {
        "create": SCOPE_ZAKEN_CREATE
        & (SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN)
    }

    viewset_classes = {
        "zaak": "openzaak.components.zaken.api.viewsets.ZaakViewSet",
    }

    extra_scopes = {"zaak": SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN}

    notification_fields = {
        "zaak": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": Zaak,
        },
        "status": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": Status,
        },
        "rollen": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": Rol,
        },
        "zaakinformatieobjecten": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": ZaakInformatieObject,
        },
        "zaakobjecten": {
            "notifications_kanaal": KANAAL_ZAKEN,
            "model": ZaakObject,
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

        self._create_audit_logs(response, serializer)
        self.notify(response.status_code, response.data)
        return response

    def _create_audit_logs(self, response, serializer):
        for field, sub_serializer in serializer.fields.items():
            is_many = getattr(sub_serializer, "many", False)

            field_data = serializer.data[field] if is_many else [serializer.data[field]]
            instances = (
                serializer.instance[field] if is_many else [serializer.instance[field]]
            )
            model = (
                sub_serializer.child.Meta.model
                if is_many
                else sub_serializer.Meta.model
            )
            basename = model._meta.model_name

            for i, data in enumerate(field_data):
                self.create_audittrail(
                    response.status_code,
                    CommonResourceAction.create,
                    version_before_edit=None,
                    version_after_edit=data,
                    unique_representation=instances[i].unique_representation(),
                    audit=AUDIT_ZRC,
                    basename=basename,
                    main_object=serializer.data["zaak"]["url"],
                )

    def perform_create(self, serializer):
        serializer.save()

        logger.info(
            "zaak_geregistreerd",
            zaak_url=serializer.data["zaak"]["url"],
            status_url=serializer.data["status"]["url"],
            zaakinformatieobjecten_urls=[
                zio["url"] for zio in serializer.data["zaakinformatieobjecten"]
            ],
            rollen_urls=[rol["url"] for rol in serializer.data["rollen"]],
            zaakobjecten_urls=[
                zaakobject["url"] for zaakobject in serializer.data["zaakobjecten"]
            ],
        )
