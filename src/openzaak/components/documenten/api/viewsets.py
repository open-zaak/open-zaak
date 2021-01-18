# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from django_sendfile import sendfile
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.settings import api_settings
from vng_api_common.audittrails.viewsets import (
    AuditTrailViewSet,
    AuditTrailViewsetMixin,
)
from vng_api_common.notifications.viewsets import NotificationViewSetMixin
from vng_api_common.serializers import FoutSerializer
from vng_api_common.viewsets import CheckQueryParamsMixin

from openzaak.utils.data_filtering import ListFilterByAuthorizationsMixin
from openzaak.utils.schema import COMMON_ERROR_RESPONSES

from ..models import (
    EnkelvoudigInformatieObject,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from .audits import AUDIT_DRC
from .filters import (
    EnkelvoudigInformatieObjectDetailFilter,
    EnkelvoudigInformatieObjectListFilter,
    GebruiksrechtenFilter,
    ObjectInformatieObjectFilter,
)
from .kanalen import KANAAL_DOCUMENTEN
from .permissions import InformationObjectAuthRequired
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
    EnkelvoudigInformatieObjectSerializer,
    EnkelvoudigInformatieObjectWithLockSerializer,
    GebruiksrechtenSerializer,
    LockEnkelvoudigInformatieObjectSerializer,
    ObjectInformatieObjectSerializer,
    UnlockEnkelvoudigInformatieObjectSerializer,
)

# Openapi query parameters for version querying
VERSIE_QUERY_PARAM = openapi.Parameter(
    "versie",
    openapi.IN_QUERY,
    description="Het (automatische) versienummer van het INFORMATIEOBJECT.",
    type=openapi.TYPE_INTEGER,
)
REGISTRATIE_QUERY_PARAM = openapi.Parameter(
    "registratieOp",
    openapi.IN_QUERY,
    description="Een datumtijd in ISO8601 formaat. De versie van het INFORMATIEOBJECT die qua `begin_registratie` het "
    "kortst hiervoor zit wordt opgehaald.",
    type=openapi.TYPE_STRING,
)


class EnkelvoudigInformatieObjectViewSet(
    CheckQueryParamsMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailViewsetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van (ENKELVOUDIG) INFORMATIEOBJECTen (documenten).

    create:
    Maak een (ENKELVOUDIG) INFORMATIEOBJECT aan.

    **Er wordt gevalideerd op**
    - geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen
      worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.
    - publicatie `informatieobjecttype` - `concept` moet `false` zijn

    list:
    Alle (ENKELVOUDIGe) INFORMATIEOBJECTen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    De objecten bevatten metadata over de documenten en de downloadlink
    (`inhoud`) naar de binary data. Alleen de laatste versie van elk
    (ENKELVOUDIG) INFORMATIEOBJECT wordt getoond. Specifieke versies kunnen
    alleen

    retrieve:
    Een specifiek (ENKELVOUDIG) INFORMATIEOBJECT opvragen.

    Het object bevat metadata over het document en de downloadlink (`inhoud`)
    naar de binary data. Dit geeft standaard de laatste versie van het
    (ENKELVOUDIG) INFORMATIEOBJECT. Specifieke versies kunnen middels
    query-string parameters worden opgevraagd.

    update:
    Werk een (ENKELVOUDIG) INFORMATIEOBJECT in zijn geheel bij.

    Dit creëert altijd een nieuwe versie van het (ENKELVOUDIG) INFORMATIEOBJECT.

    **Er wordt gevalideerd op**
    - correcte `lock` waarde
    - geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen
      worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.
    - publicatie `informatieobjecttype` - `concept` moet `false` zijn
    - status NIET `definitief`

    *TODO*
    - valideer immutable attributes

    partial_update:
    Werk een (ENKELVOUDIG) INFORMATIEOBJECT deels bij.

    Dit creëert altijd een nieuwe versie van het (ENKELVOUDIG) INFORMATIEOBJECT.

    **Er wordt gevalideerd op**
    - correcte `lock` waarde
    - geldigheid `informatieobjecttype` URL - de resource moet opgevraagd kunnen
      worden uit de catalogi API en de vorm van een INFORMATIEOBJECTTYPE hebben.
    - publicatie `informatieobjecttype` - `concept` moet `false` zijn
    - status NIET `definitief`

    *TODO*
    - valideer immutable attributes

    destroy:
    Verwijder een (ENKELVOUDIG) INFORMATIEOBJECT.

    Verwijder een (ENKELVOUDIG) INFORMATIEOBJECT en alle bijbehorende versies,
    samen met alle gerelateerde resources binnen deze API. Dit is alleen mogelijk
    als er geen OBJECTINFORMATIEOBJECTen relateerd zijn aan het (ENKELVOUDIG)
    INFORMATIEOBJECT.

    **Gerelateerde resources**
    - GEBRUIKSRECHTen
    - audit trail regels

    download:
    Download de binaire data van het (ENKELVOUDIG) INFORMATIEOBJECT.

    Download de binaire data van het (ENKELVOUDIG) INFORMATIEOBJECT.

    lock:
    Vergrendel een (ENKELVOUDIG) INFORMATIEOBJECT.

    Voert een "checkout" uit waardoor het (ENKELVOUDIG) INFORMATIEOBJECT
    vergrendeld wordt met een `lock` waarde. Alleen met deze waarde kan het
    (ENKELVOUDIG) INFORMATIEOBJECT bijgewerkt (`PUT`, `PATCH`) en weer
    ontgrendeld worden.

    unlock:
    Ontgrendel een (ENKELVOUDIG) INFORMATIEOBJECT.

    Heft de "checkout" op waardoor het (ENKELVOUDIG) INFORMATIEOBJECT
    ontgrendeld wordt.
    """

    queryset = (
        EnkelvoudigInformatieObject.objects.select_related(
            "canonical", "_informatieobjecttype"
        )
        .order_by("canonical", "-versie")
        .distinct("canonical")
    )
    lookup_field = "uuid"
    serializer_class = EnkelvoudigInformatieObjectSerializer
    pagination_class = PageNumberPagination
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
    }
    notifications_kanaal = KANAAL_DOCUMENTEN
    audit = AUDIT_DRC

    @property
    def swagger_schema(self):
        # Ensure that schema is not imported at module level, needed to
        # properly generate notification documentation for API schema
        from .schema import EIOAutoSchema

        return EIOAutoSchema

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
        if getattr(self, "action", None) in ["update", "partial_update"]:
            return EnkelvoudigInformatieObjectWithLockSerializer
        return super().get_serializer_class()

    @swagger_auto_schema(
        manual_parameters=[VERSIE_QUERY_PARAM, REGISTRATIE_QUERY_PARAM]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        method="get",
        # see https://swagger.io/docs/specification/2-0/describing-responses/ and
        # https://swagger.io/docs/specification/2-0/mime-types/
        # OAS 3 has a better mechanism: https://swagger.io/docs/specification/describing-responses/
        produces=["application/octet-stream"],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "De binaire bestandsinhoud",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            **COMMON_ERROR_RESPONSES,
        },
        manual_parameters=[VERSIE_QUERY_PARAM, REGISTRATIE_QUERY_PARAM],
    )
    @action(methods=["get"], detail=True, name="enkelvoudiginformatieobject_download")
    def download(self, request, *args, **kwargs):
        eio = self.get_object()
        if settings.CMIS_ENABLED:
            return FileResponse(eio.inhoud.file, as_attachment=True)
        else:
            return sendfile(
                request,
                eio.inhoud.path,
                attachment=True,
                mimetype="application/octet-stream",
            )

    @swagger_auto_schema(
        request_body=LockEnkelvoudigInformatieObjectSerializer,
        responses={
            status.HTTP_200_OK: LockEnkelvoudigInformatieObjectSerializer,
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                "Bad request", schema=FoutSerializer
            ),
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"])
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

    @swagger_auto_schema(
        request_body=UnlockEnkelvoudigInformatieObjectSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Response("No content"),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                "Bad request", schema=FoutSerializer
            ),
            **COMMON_ERROR_RESPONSES,
        },
    )
    @action(detail=True, methods=["post"])
    def unlock(self, request, *args, **kwargs):
        eio = self.get_object()
        eio_data = self.get_serializer(eio).data
        canonical = eio.canonical

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
            canonical,
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


class GebruiksrechtenViewSet(
    CheckQueryParamsMixin,
    NotificationViewSetMixin,
    ListFilterByAuthorizationsMixin,
    AuditTrailViewsetMixin,
    viewsets.ModelViewSet,
):
    """
    Opvragen en bewerken van GEBRUIKSRECHTen bij een INFORMATIEOBJECT.

    create:
    Maak een GEBRUIKSRECHT aan.

    Voeg GEBRUIKSRECHTen toe voor een INFORMATIEOBJECT.

    **Opmerkingen**
    - Het toevoegen van gebruiksrechten zorgt ervoor dat de
      `indicatieGebruiksrecht` op het informatieobject op `true` gezet wordt.

    list:
    Alle GEBRUIKSRECHTen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke GEBRUIKSRECHT opvragen.

    Een specifieke GEBRUIKSRECHT opvragen.

    update:
    Werk een GEBRUIKSRECHT in zijn geheel bij.

    Werk een GEBRUIKSRECHT in zijn geheel bij.

    partial_update:
    Werk een GEBRUIKSRECHT relatie deels bij.

    Werk een GEBRUIKSRECHT relatie deels bij.

    destroy:
    Verwijder een GEBRUIKSRECHT.

    **Opmerkingen**
    - Indien het laatste GEBRUIKSRECHT van een INFORMATIEOBJECT verwijderd
      wordt, dan wordt de `indicatieGebruiksrecht` van het INFORMATIEOBJECT op
      `null` gezet.
    """

    queryset = (
        Gebruiksrechten.objects.select_related("informatieobject")
        .prefetch_related("informatieobject__enkelvoudiginformatieobject_set")
        .all()
    )
    serializer_class = GebruiksrechtenSerializer
    filterset_class = GebruiksrechtenFilter
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


class EnkelvoudigInformatieObjectAuditTrailViewSet(AuditTrailViewSet):
    """
    Opvragen van de audit trail regels.

    list:
    Alle audit trail regels behorend bij het INFORMATIEOBJECT.

    Alle audit trail regels behorend bij het INFORMATIEOBJECT.

    retrieve:
    Een specifieke audit trail regel opvragen.

    Een specifieke audit trail regel opvragen.
    """

    main_resource_lookup_field = "enkelvoudiginformatieobject_uuid"


class ObjectInformatieObjectViewSet(
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

    create:
    Maak een OBJECT-INFORMATIEOBJECT relatie aan.

    **LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**

    Andere API's, zoals de Zaken API en de Besluiten API, gebruiken dit
    endpoint bij het synchroniseren van relaties.

    **Er wordt gevalideerd op**
    - geldigheid `informatieobject` URL
    - de combinatie `informatieobject` en `object` moet uniek zijn
    - bestaan van `object` URL

    list:
    Alle OBJECT-INFORMATIEOBJECT relaties opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke OBJECT-INFORMATIEOBJECT relatie opvragen.

    Een specifieke OBJECT-INFORMATIEOBJECT relatie opvragen.

    destroy:
    Verwijder een OBJECT-INFORMATIEOBJECT relatie.

    **LET OP: Dit endpoint hoor je als consumer niet zelf aan te spreken.**

    Andere API's, zoals de Zaken API en de Besluiten API, gebruiken dit
    endpoint bij het synchroniseren van relaties.
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
        object = serializer.validated_data["object"]

        # external object
        if isinstance(object, ProxyMixin):
            super().perform_create(serializer)
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
        # external object
        if isinstance(instance.object, ProxyMixin):
            super().perform_destroy(instance)
            return

        if (
            instance.object_type == "zaak"
            and instance.does_zaakinformatieobject_exist()
        ):
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The relation between zaak and informatieobject still exists"
                    )
                },
                code="inconsistent-relation",
            )

        if (
            instance.object_type == "besluit"
            and instance.does_besluitinformatieobject_exist()
        ):
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The relation between besluit and informatieobject still exists"
                    )
                },
                code="inconsistent-relation",
            )
