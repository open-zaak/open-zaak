from django.contrib import admin, messages
from django.db.models import Field
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from openzaak.selectielijst.admin import get_procestype_field
from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
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
from .mixins import GeldigheidAdminMixin
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
    DynamicArrayMixin,
    admin.ModelAdmin,
):
    model = ZaakType
    form = ZaakTypeForm

    # List
    list_display = (
        "identificatie",
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
    ordering = ("catalogus", "identificatie")
    search_fields = (
        "identificatie",
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

    def response_post_save_change(self, request, obj):
        if "_publish" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            if (
                obj.besluittypen.filter(concept=True).exists()
                or obj.informatieobjecttypen.filter(concept=True).exists()
            ):
                msg = _("All related resources should be published")
                self.message_user(request, msg, level=messages.ERROR)
            else:
                obj.concept = False
                obj.save()
                msg = _("The resource has been published successfully!")
                self.message_user(request, msg, level=messages.SUCCESS)

            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)

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
