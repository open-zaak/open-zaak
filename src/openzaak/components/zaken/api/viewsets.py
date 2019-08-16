import logging

from django.shortcuts import get_object_or_404

from openzaak.components.zaken.models import (
    KlantContact, Resultaat, Rol, Status, Zaak, ZaakEigenschap,
    ZaakInformatieObject, ZaakObject
)
from openzaak.utils.data_filtering import ListFilterByAuthorizationsMixin
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from vng_api_common.audittrails.viewsets import (
    AuditTrailCreateMixin, AuditTrailViewSet, AuditTrailViewsetMixin
)
from vng_api_common.filters import Backend
from vng_api_common.geo import GeoMixin
from vng_api_common.notifications.viewsets import (
    NotificationCreateMixin, NotificationViewSetMixin
)
from vng_api_common.permissions import permission_class_factory
from vng_api_common.search import SearchMixin
from vng_api_common.utils import lookup_kwargs_to_filters
from vng_api_common.viewsets import CheckQueryParamsMixin, NestedViewSetMixin

from .audits import AUDIT_ZRC
from .filters import (
    ResultaatFilter, RolFilter, StatusFilter, ZaakFilter,
    ZaakInformatieObjectFilter, ZaakObjectFilter
)
from .kanalen import KANAAL_ZAKEN
from .permissions import (
    ZaakAuthScopesRequired, ZaakBaseAuthRequired,
    ZaakRelatedAuthScopesRequired
)
from .scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN, SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN, SCOPEN_ZAKEN_HEROPENEN
)
from .serializers import (
    KlantContactSerializer, ResultaatSerializer, RolSerializer,
    StatusSerializer, ZaakEigenschapSerializer, ZaakInformatieObjectSerializer,
    ZaakObjectSerializer, ZaakSerializer, ZaakZoekSerializer
)

logger = logging.getLogger(__name__)


class ZaakViewSet(NotificationViewSetMixin,
                  AuditTrailViewsetMixin,
                  GeoMixin,
                  SearchMixin,
                  CheckQueryParamsMixin,
                  # ListFilterByAuthorizationsMixin,
                  viewsets.ModelViewSet):
    """
    Opvragen en bewerken van ZAAKen.

    Een zaak mag (in principe) niet meer gewijzigd worden als de
    `archiefstatus` een andere status heeft dan "nog_te_archiveren". Voor
    praktische redenen is er geen harde validatie regel aan de provider kant.

    create:
    Maak een ZAAK aan.

    Indien geen identificatie gegeven is, dan wordt deze automatisch
    gegenereerd. De identificatie moet uniek zijn binnen de bronorganisatie.

    **Er wordt gevalideerd op**:
    - `zaaktype` moet een geldige URL zijn.
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    list:
    Alle ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    **Opmerking**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.

    retrieve:
    Een specifieke ZAAK opvragen.

    Een specifieke ZAAK opvragen.

    update:
    Werk een ZAAK in zijn geheel bij.

    **Er wordt gevalideerd op**
    - `zaaktype` mag niet gewijzigd worden.
    - `identificatie` mag niet gewijzigd worden.
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    **Opmerkingen**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.
    - zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.
    - indien een zaak heropend moet worden, doe dit dan door een nieuwe status
      toe te voegen die NIET de eindstatus is.
      Zie de `Status` resource.

    partial_update:
    Werk een ZAAK deels bij.

    **Er wordt gevalideerd op**
    - `zaaktype` mag niet gewijzigd worden.
    - `identificatie` mag niet gewijzigd worden.
    - `laatsteBetaaldatum` mag niet in de toekomst liggen.
    - `laatsteBetaaldatum` mag niet gezet worden als de betalingsindicatie
      "nvt" is.
    - `archiefnominatie` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefactiedatum` moet een waarde hebben indien `archiefstatus` niet de
      waarde "nog_te_archiveren" heeft.
    - `archiefstatus` kan alleen een waarde anders dan "nog_te_archiveren"
      hebben indien van alle gerelateeerde INFORMATIEOBJECTen het attribuut
      `status` de waarde "gearchiveerd" heeft.

    **Opmerkingen**
    - er worden enkel zaken getoond van de zaaktypes waar u toe geautoriseerd
      bent.
    - zaaktype zal in de toekomst niet-wijzigbaar gemaakt worden.
    - indien een zaak heropend moet worden, doe dit dan door een nieuwe status
      toe te voegen die NIET de eindstatus is. Zie de `Status` resource.

    destroy:
    Verwijder een ZAAK.

    **De gerelateerde resources zijn hierbij**
    - `zaak` - de deelzaken van de verwijderde hoofzaak
    - `status` - alle statussen van de verwijderde zaak
    - `resultaat` - het resultaat van de verwijderde zaak
    - `rol` - alle rollen bij de zaak
    - `zaakobject` - alle zaakobjecten bij de zaak
    - `zaakeigenschap` - alle eigenschappen van de zaak
    - `zaakkenmerk` - alle kenmerken van de zaak
    - `zaakinformatieobject` - dit moet door-cascaden naar de Documenten API,
      zie ook: https://github.com/VNG-Realisatie/gemma-zaken/issues/791 (TODO)
    - `klantcontact` - alle klantcontacten bij een zaak
    """
    queryset = Zaak.objects.prefetch_related('deelzaken').order_by('-pk')
    serializer_class = ZaakSerializer
    search_input_serializer_class = ZaakZoekSerializer
    filter_backends = (Backend, OrderingFilter)
    filterset_class = ZaakFilter
    ordering_fields = ('startdatum', )
    lookup_field = 'uuid'
    pagination_class = PageNumberPagination

    # permission_classes = (ZaakAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        '_zoek': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_CREATE,
        'update': SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        'partial_update': SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        'destroy': SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    @action(methods=('post',), detail=False)
    def _zoek(self, request, *args, **kwargs):
        """
        Voer een (geo)-zoekopdracht uit op ZAAKen.

        Zoeken/filteren gaat normaal via de `list` operatie, deze is echter
        niet geschikt voor geo-zoekopdrachten.
        """
        search_input = self.get_search_input()

        within = search_input['zaakgeometrie']['within']
        queryset = (
            self
            .filter_queryset(self.get_queryset())
            .filter(zaakgeometrie__within=within)
        )

        return self.get_search_output(queryset)
    _zoek.is_search_action = True

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

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
            zaaktype=zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding
        ):
            if zaak.einddatum:
                msg = "Modifying a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)
        super().perform_update(serializer)


class StatusViewSet(NotificationCreateMixin,
                    AuditTrailCreateMixin,
                    CheckQueryParamsMixin,
                    # ListFilterByAuthorizationsMixin,
                    mixins.CreateModelMixin,
                    viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en beheren van zaakstatussen.

    list:
    Alle STATUSsen van ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke STATUS van een ZAAK opvragen.

    Een specifieke STATUS van een ZAAK opvragen.

    create:
    Maak een STATUS aan voor een ZAAK.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - geldigheid URL naar het STATUSTYPE
    - indien het de eindstatus betreft, dan moet het attribuut
      `indicatieGebruiksrecht` gezet zijn op alle informatieobjecten die aan
      de zaak gerelateerd zijn

    **Opmerkingen**
    - Indien het statustype de eindstatus is (volgens het ZTC), dan wordt de
      zaak afgesloten door de einddatum te zetten.

    """
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    filterset_class = StatusFilter
    lookup_field = 'uuid'

    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_CREATE | SCOPE_STATUSSEN_TOEVOEGEN | SCOPEN_ZAKEN_HEROPENEN,
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
        zaak = serializer.validated_data['zaak']
        if not self.request.jwt_auth.has_auth(
            scopes=SCOPE_STATUSSEN_TOEVOEGEN | SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding
        ):
            if zaak.status_set.exists():
                msg = f"Met de '{SCOPE_ZAKEN_CREATE}' scope mag je slechts 1 status zetten"
                raise PermissionDenied(detail=msg)

        if not self.request.jwt_auth.has_auth(
            scopes=SCOPEN_ZAKEN_HEROPENEN,
            zaaktype=zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding
        ):
            if zaak.einddatum:
                msg = "Reopening a closed case with current scope is forbidden"
                raise PermissionDenied(detail=msg)

        super().perform_create(serializer)


class ZaakObjectViewSet(NotificationCreateMixin,
                        # ListFilterByAuthorizationsMixin,
                        AuditTrailCreateMixin,
                        mixins.CreateModelMixin,
                        viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en bewerken van ZAAKOBJECTen.

    create:
    Maak een ZAAKOBJECT aan.

    Maak een ZAAKOBJECT aan.

    list:
    Alle ZAAKOBJECTen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifiek ZAAKOBJECT opvragen.

    Een specifiek ZAAKOBJECT opvragen.
    """
    queryset = ZaakObject.objects.all()
    serializer_class = ZaakObjectSerializer
    filterset_class = ZaakObjectFilter
    lookup_field = 'uuid'

    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_CREATE | SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ZaakInformatieObjectViewSet(NotificationCreateMixin,
                                  AuditTrailViewsetMixin,
                                  CheckQueryParamsMixin,
                                  # ListFilterByAuthorizationsMixin,
                                  viewsets.ModelViewSet):

    """
    Opvragen en bewerken van ZAAK-INFORMATIEOBJECT relaties.

    create:
    Maak een ZAAK-INFORMATIEOBJECT relatie aan.

    Er worden twee types van
    relaties met andere objecten gerealiseerd:

    **Er wordt gevalideerd op**
    - geldigheid zaak URL
    - geldigheid informatieobject URL
    - de combinatie informatieobject en zaak moet uniek zijn

    **Opmerkingen**
    - De registratiedatum wordt door het systeem op 'NU' gezet. De `aardRelatie`
      wordt ook door het systeem gezet.
    - Bij het aanmaken wordt ook in de Documenten API de gespiegelde relatie aangemaakt,
      echter zonder de relatie-informatie.

    Registreer welk(e) INFORMATIEOBJECT(en) een ZAAK kent.

    **Er wordt gevalideerd op**
    - geldigheid informatieobject URL
    - uniek zijn van relatie ZAAK-INFORMATIEOBJECT

    list:
    Alle ZAAK-INFORMATIEOBJECT relaties opvragen.

    Deze lijst kan gefilterd wordt met querystringparameters.

    retrieve:
    Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.

    Een specifieke ZAAK-INFORMATIEOBJECT relatie opvragen.

    update:
    Werk een ZAAK-INFORMATIEOBJECT relatie in zijn geheel bij.

    Je mag enkel de gegevens
    van de relatie bewerken, en niet de relatie zelf aanpassen.

    **Er wordt gevalideerd op**
    - informatieobject URL en zaak URL mogen niet veranderen

    partial_update:
    Werk een ZAAK-INFORMATIEOBJECT relatie in deels bij.

    Je mag enkel de gegevens
    van de relatie bewerken, en niet de relatie zelf aanpassen.

    **Er wordt gevalideerd op**
    - informatieobject URL en zaak URL mogen niet veranderen

    destroy:
    Verwijder een ZAAK-INFORMATIEOBJECT relatie.

    De gespiegelde relatie in de Documenten API wordt door de Zaken API verwijderd. Consumers kunnen dit niet handmatig doen..
    """
    queryset = ZaakInformatieObject.objects.all()
    filterset_class = ZaakInformatieObjectFilter
    serializer_class = ZaakInformatieObjectSerializer
    lookup_field = 'uuid'
    notifications_kanaal = KANAAL_ZAKEN
    notifications_main_resource_key = 'zaak'

    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_CREATE | SCOPE_ZAKEN_BIJWERKEN,
        'update': SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        'partial_update': SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
        'destroy': SCOPE_ZAKEN_BIJWERKEN | SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN | SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    }
    audit = AUDIT_ZRC


class ZaakEigenschapViewSet(NotificationCreateMixin,
                            AuditTrailCreateMixin,
                            NestedViewSetMixin,
                            # ListFilterByAuthorizationsMixin,
                            mixins.CreateModelMixin,
                            viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en bewerken van ZAAKEIGENSCHAPpen

    create:
    Maak een ZAAKEIGENSCHAP aan.

    Maak een ZAAKEIGENSCHAP aan.

    list:
    Alle ZAAKEIGENSCHAPpen opvragen.

    Alle ZAAKEIGENSCHAPpen opvragen.

    retrieve:
    Een specifieke ZAAKEIGENSCHAP opvragen.

    Een specifieke ZAAKEIGENSCHAP opvragen.
    """
    queryset = ZaakEigenschap.objects.all()
    serializer_class = ZaakEigenschapSerializer
    # permission_classes = (
    #     permission_class_factory(
    #         base=ZaakBaseAuthRequired,
    #         get_obj='_get_zaak',
    #     ),
    # )
    lookup_field = 'uuid'
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_BIJWERKEN,
        'destroy': SCOPE_ZAKEN_BIJWERKEN,
    }
    parent_retrieve_kwargs = {
        'zaak_uuid': 'uuid',
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC

    def _get_zaak(self):
        if not hasattr(self, '_zaak'):
            filters = lookup_kwargs_to_filters(self.parent_retrieve_kwargs, self.kwargs)
            self._zaak = get_object_or_404(Zaak, **filters)
        return self._zaak

    def list(self, request, *args, **kwargs):
        zaak = self._get_zaak()
        permission = ZaakAuthScopesRequired()
        if not permission.has_object_permission(self.request, self, zaak):
            raise PermissionDenied
        return super().list(request, *args, **kwargs)


class KlantContactViewSet(NotificationCreateMixin,
                          # ListFilterByAuthorizationsMixin,
                          AuditTrailCreateMixin,
                          mixins.CreateModelMixin,
                          viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en bewerken van KLANTCONTACTen.

    create:
    Maak een KLANTCONTACT bij een ZAAK aan.

    Indien geen identificatie gegeven is, dan wordt deze automatisch
    gegenereerd.

    list:
    Alle KLANTCONTACTen opvragen.

    Alle KLANTCONTACTen opvragen.

    retrieve:
    Een specifiek KLANTCONTACT bij een ZAAK opvragen.

    Een specifiek KLANTCONTACT bij een ZAAK opvragen.
    """
    queryset = KlantContact.objects.all()
    serializer_class = KlantContactSerializer
    lookup_field = 'uuid'
    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class RolViewSet(NotificationCreateMixin,
                 AuditTrailCreateMixin,
                 CheckQueryParamsMixin,
                 # ListFilterByAuthorizationsMixin,
                 mixins.CreateModelMixin,
                 mixins.DestroyModelMixin,
                 viewsets.ReadOnlyModelViewSet):
    """
    Opvragen en bewerken van ROL relatie tussen een ZAAK en een BETROKKENE.

    list:
    Alle ROLlen bij ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ROL bij een ZAAK opvragen.

    Een specifieke ROL bij een ZAAK opvragen.

    destroy:
    Verwijder een ROL van een ZAAK.

    Verwijder een ROL van een ZAAK.

    create:
    Maak een ROL aan bij een ZAAK.

    Maak een ROL aan bij een ZAAK.

    """
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    filterset_class = RolFilter
    lookup_field = 'uuid'

    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_BIJWERKEN,
        'destroy': SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ResultaatViewSet(NotificationViewSetMixin,
                       AuditTrailViewsetMixin,
                       CheckQueryParamsMixin,
                       # ListFilterByAuthorizationsMixin,
                       viewsets.ModelViewSet):
    """
    Opvragen en beheren van resultaten.

    list:
    Alle RESULTAATen van ZAAKen opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifiek RESULTAAT opvragen.

    Een specifiek RESULTAAT opvragen.

    create:
    Maak een RESULTAAT bij een ZAAK aan.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - geldigheid URL naar het RESULTAATTYPE

    update:
    Werk een RESULTAAT in zijn geheel bij.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - het RESULTAATTYPE mag niet gewijzigd worden

    partial_update:
    Werk een RESULTAAT deels bij.

    **Er wordt gevalideerd op**
    - geldigheid URL naar de ZAAK
    - het RESULTAATTYPE mag niet gewijzigd worden

    destroy:
    Verwijder een RESULTAAT van een ZAAK.

    Verwijder een RESULTAAT van een ZAAK.

    """
    queryset = Resultaat.objects.all()
    serializer_class = ResultaatSerializer
    filterset_class = ResultaatFilter
    lookup_field = 'uuid'

    # permission_classes = (ZaakRelatedAuthScopesRequired,)
    required_scopes = {
        'list': SCOPE_ZAKEN_ALLES_LEZEN,
        'retrieve': SCOPE_ZAKEN_ALLES_LEZEN,
        'create': SCOPE_ZAKEN_BIJWERKEN,
        'destroy': SCOPE_ZAKEN_BIJWERKEN,
        'update': SCOPE_ZAKEN_BIJWERKEN,
        'partial_update': SCOPE_ZAKEN_BIJWERKEN,
    }
    notifications_kanaal = KANAAL_ZAKEN
    audit = AUDIT_ZRC


class ZaakAuditTrailViewSet(AuditTrailViewSet):
    """
    Opvragen van Audit trails horend bij een ZAAK.

    list:
    Alle audit trail regels behorend bij de ZAAK.

    Alle audit trail regels behorend bij de ZAAK.

    retrieve:
    Een specifieke audit trail regel opvragen.

    Een specifieke audit trail regel opvragen.
    """
    main_resource_lookup_field = 'zaak_uuid'
