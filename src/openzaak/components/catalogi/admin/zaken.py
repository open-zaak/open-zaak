from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
)

from ..models import (
    BronCatalogus,
    BronZaakType,
    Eigenschap,
    Formulier,
    ResultaatType,
    RolType,
    StatusType,
    ZaakObjectType,
    ZaakType,
    ZaakTypenRelatie,
)
from .eigenschap import EigenschapAdmin
from .forms import ZaakTypeForm
from .mixins import (
    ConceptAdminMixin,
    FilterSearchOrderingAdminMixin,
    GeldigheidAdminMixin,
)
from .resultaattype import ResultaatTypeAdmin
from .roltype import RolTypeAdmin
from .statustype import StatusTypeAdmin


@admin.register(ZaakObjectType)
class ZaakObjectTypeAdmin(
    GeldigheidAdminMixin, FilterSearchOrderingAdminMixin, admin.ModelAdmin
):
    model = ZaakObjectType

    # List
    list_display = ["objecttype", "ander_objecttype", "statustype"]

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "objecttype",
                    "ander_objecttype",
                    "relatieomschrijving",
                    "statustype",
                )
            },
        ),
        (_("Relaties"), {"fields": ("is_relevant_voor",)}),
    )
    raw_id_fields = ("is_relevant_voor", "statustype")


class StatusTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = StatusType
    fields = StatusTypeAdmin.list_display
    fk_name = "zaaktype"


class ZaakObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakObjectType
    fields = ZaakObjectTypeAdmin.list_display
    fk_name = "is_relevant_voor"


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
    FilterSearchOrderingAdminMixin,
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
        "zaakcategorie",
        "catalogus",
        "uuid",
        "get_absolute_api_url",
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
                    "zaakcategorie",
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
                    "archiefclassificatiecode",
                    "vertrouwelijkheidaanduiding",
                    "verantwoordelijke",
                    "producten_of_diensten",
                    "formulier",  # m2m
                    "verantwoordingsrelatie",
                    "versiedatum",  # ??
                    "broncatalogus",  #
                    "bronzaaktype",  # dit is het model
                )
            },
        ),
        (_("Gemeentelijke selectielijst"), {"fields": ("selectielijst_procestype",)}),
        (
            _("Referentieproces"),
            {"fields": ("referentieproces_naam", "referentieproces_link")},
        ),
        (_("Publicatie"), {"fields": ("publicatie_indicatie", "publicatietekst")}),
        (
            _("Relaties"),
            {
                "fields": (
                    "catalogus",
                    # m2m:
                    "is_deelzaaktype_van",
                )
            },
        ),
    )
    filter_horizontal = ("is_deelzaaktype_van", "formulier")
    raw_id_fields = ("catalogus",)
    inlines = (
        ZaakTypenRelatieInline,
        StatusTypeInline,
        ZaakObjectTypeInline,
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
                _("Toon {}").format(ZaakObjectType._meta.verbose_name_plural),
                self._build_changelist_url(
                    ZaakObjectType, query={"is_relevant_voor": obj.pk}
                ),
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


#
# models for ZaakType
#


@admin.register(Formulier)
class FormulierAdmin(admin.ModelAdmin):
    list_display = ["naam"]
    fields = ("naam", "link")


@admin.register(BronCatalogus)
class BronCatalogusAdmin(admin.ModelAdmin):
    list_display = ["domein", "rsin"]
    fields = ("domein", "rsin")


@admin.register(BronZaakType)
class BronZaakTypeAdmin(admin.ModelAdmin):
    list_display = ["zaaktype_identificatie", "zaaktype_omschrijving"]
    fields = ("zaaktype_identificatie", "zaaktype_omschrijving")
