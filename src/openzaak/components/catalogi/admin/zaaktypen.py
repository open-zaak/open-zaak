from django.apps import apps
from django.contrib import admin
from django.db.models import Field
from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _

from openzaak.selectielijst.admin import get_procestype_field
from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
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
from .mixins import (
    CatalogusContextAdminMixin,
    ExportMixin,
    NewVersionMixin,
    PublishAdminMixin,
)
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
    fk_name = "zaaktype"


class EigenschapInline(EditInlineAdminMixin, admin.TabularInline):
    model = Eigenschap
    fields = EigenschapAdmin.list_display
    fk_name = "zaaktype"


class ResultaatTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ResultaatType
    fields = ResultaatTypeAdmin.list_display
    fk_name = "zaaktype"


class ZaakTypenRelatieInline(admin.TabularInline):
    model = ZaakTypenRelatie
    fk_name = "zaaktype"
    extra = 1


@admin.register(ZaakType)
class ZaakTypeAdmin(
    NewVersionMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    PublishAdminMixin,
    ExportMixin,
    DynamicArrayMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = ZaakType
    form = ZaakTypeForm

    # List
    list_display = (
        "zaaktype_omschrijving",
        "identificatie",
        "versiedatum",
        "is_published",
    )
    list_filter = (
        "catalogus",
        "publicatie_indicatie",
        "verlenging_mogelijk",
        "opschorting_en_aanhouding_mogelijk",
        "indicatie_intern_of_extern",
        "vertrouwelijkheidaanduiding",
    )
    ordering = ("catalogus", "identificatie")
    search_fields = (
        "uuid",
        "identificatie",
        "zaaktype_omschrijving",
        "zaaktype_omschrijving_generiek",
        "zaakcategorie",
        "doel",
        "aanleiding",
        "onderwerp",
        "toelichting",
    )
    date_hierarchy = "versiedatum"

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "identificatie",
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
        (
            _("Geldigheid"),
            {
                "fields": (
                    "versiedatum",
                    "datum_begin_geldigheid",
                    "datum_einde_geldigheid",
                )
            },
        ),
    )
    raw_id_fields = ("catalogus",)
    readonly_fields = ("versiedatum",)
    inlines = (
        ZaakTypenRelatieInline,
        StatusTypeInline,
        RolTypeInline,
        EigenschapInline,
        ResultaatTypeInline,
    )
    change_form_template = "admin/catalogi/change_form_zaaktype.html"
    exclude_copy_relation = ("zaak",)

    # For export mixin
    resource_name = "zaaktype"

    def get_related_objects(self, obj):
        resources = {}

        resources["ZaakType"] = [obj.pk]

        # M2M relations
        resources["BesluitType"] = list(obj.besluittypen.values_list("pk", flat=True))
        resources["InformatieObjectType"] = list(
            obj.informatieobjecttypen.values_list("pk", flat=True)
        )

        resources["ZaakTypeInformatieObjectType"] = list(
            obj.zaaktypeinformatieobjecttype_set.values_list("pk", flat=True)
        )

        # Resources with foreign keys to ZaakType
        fields = ["ResultaatType", "RolType", "StatusType", "Eigenschap"]
        for field in fields:
            model = apps.get_model("catalogi", field)
            resources[field] = list(
                model.objects.filter(zaaktype=obj).values_list("pk", flat=True)
            )

        resource_list = []
        id_list = []
        for resource, ids in resources.items():
            if ids:
                resource_list.append(resource)
                id_list.append(ids)

        return resource_list, id_list

    def _publish_validation_errors(self, obj):
        errors = []
        if (
            obj.besluittypen.filter(concept=True).exists()
            or obj.informatieobjecttypen.filter(concept=True).exists()
        ):
            errors.append(_("All related resources should be published"))
        return errors

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(StatusType, obj),
            link_to_related_objects(RolType, obj),
            link_to_related_objects(Eigenschap, obj),
            link_to_related_objects(ResultaatType, obj),
        )

    def formfield_for_dbfield(self, db_field: Field, request: HttpRequest, **kwargs):
        if db_field.name == "selectielijst_procestype":
            return get_procestype_field(db_field, request, **kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.versiedatum = obj.datum_begin_geldigheid

        super().save_model(request, obj, form, change)
