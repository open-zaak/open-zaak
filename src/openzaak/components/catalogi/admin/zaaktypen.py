from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
)

from ..models import (
    Eigenschap,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypenRelatie,
)
from .eigenschap import EigenschapAdmin
from .forms import ZaakTypeForm
from .mixins import ConceptAdminMixin, GeldigheidAdminMixin
from .resultaattype import ResultaatTypeAdmin
from .roltype import RolTypeAdmin
from .statustype import StatusTypeAdmin


class StatusTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = StatusType
    fields = StatusTypeAdmin.list_display
    fk_name = "zaaktype"


class RolTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = RolType
    fields = RolTypeAdmin.list_display


class EigenschapInline(EditInlineAdminMixin, admin.TabularInline):
    model = Eigenschap
    fields = EigenschapAdmin.list_display
    fk_name = "zaaktype"


class ResultaatTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ResultaatType
    fields = ResultaatTypeAdmin.list_display


class ZaakTypenRelatieInline(admin.TabularInline):
    model = ZaakTypenRelatie
    fk_name = "zaaktype"
    extra = 1


@admin.register(ZaakType)
class ZaakTypeAdmin(
    ListObjectActionsAdminMixin,
    GeldigheidAdminMixin,
    ConceptAdminMixin,
    DynamicArrayMixin,
    admin.ModelAdmin,
):
    model = ZaakType
    form = ZaakTypeForm

    # List
    list_display = (
        "zaaktype_identificatie",
        "zaaktype_omschrijving",
        "catalogus",
        "uuid",
        "get_absolute_api_url",
    )
    list_filter = (
        "catalogus",
        "publicatie_indicatie",
        "verlenging_mogelijk",
        "opschorting_en_aanhouding_mogelijk",
        "indicatie_intern_of_extern",
        "vertrouwelijkheidaanduiding",
    )
    ordering = ("catalogus", "zaaktype_identificatie")
    search_fields = (
        "zaaktype_identificatie",
        "zaaktype_omschrijving",
        "zaaktype_omschrijving_generiek",
        "zaakcategorie",
        "doel",
        "aanleiding",
        "onderwerp",
        "toelichting",
    )

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "zaaktype_identificatie",
                    "zaaktype_omschrijving",
                    "zaaktype_omschrijving_generiek",
                    "doel",
                    "aanleiding",
                    "toelichting",
                    "indicatie_intern_of_extern",
                    "handeling_initiator",
                    "onderwerp",
                    "handeling_behandelaar",
                    "doorlooptijd_behandeling",
                    "servicenorm_behandeling",
                    "opschorting_en_aanhouding_mogelijk",
                    "verlenging_mogelijk",
                    "verlengingstermijn",
                    "trefwoorden",
                    "vertrouwelijkheidaanduiding",
                    "producten_of_diensten",
                    "verantwoordingsrelatie",
                    "versiedatum",  # ??
                )
            },
        ),
        (_("Gemeentelijke selectielijst"), {"fields": ("selectielijst_procestype",)}),
        (
            _("Referentieproces"),
            {"fields": ("referentieproces_naam", "referentieproces_link")},
        ),
        (_("Publicatie"), {"fields": ("publicatie_indicatie", "publicatietekst")}),
        (_("Relaties"), {"fields": ("catalogus",)}),
    )
    raw_id_fields = ("catalogus",)
    inlines = (
        ZaakTypenRelatieInline,
        StatusTypeInline,
        RolTypeInline,
        EigenschapInline,
        ResultaatTypeInline,
    )

    def get_object_actions(self, obj):
        return (
            (
                _("Toon {}").format(StatusType._meta.verbose_name_plural),
                self._build_changelist_url(StatusType, query={"is_van": obj.pk}),
            ),
            (
                _("Toon {}").format(RolType._meta.verbose_name_plural),
                self._build_changelist_url(RolType, query={"is_van": obj.pk}),
            ),
            (
                _("Toon {}").format(Eigenschap._meta.verbose_name_plural),
                self._build_changelist_url(Eigenschap, query={"is_van": obj.pk}),
            ),
            (
                _("Toon {}").format(ResultaatType._meta.verbose_name_plural),
                self._build_changelist_url(
                    ResultaatType, query={"is_relevant_voor": obj.pk}
                ),
            ),
        )
