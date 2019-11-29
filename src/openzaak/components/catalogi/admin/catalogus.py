from django.contrib import admin
from django.urls import path
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..models import BesluitType, Catalogus, InformatieObjectType, ZaakType
from .besluittype import BesluitTypeAdmin
from .informatieobjecttype import InformatieObjectTypeAdmin
from .mixins import CatalogusImportExportMixin
from .zaaktypen import ZaakTypeAdmin


class ZaakTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakType
    fields = ZaakTypeAdmin.list_display
    fk_name = "catalogus"


class BesluitTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitType
    fields = BesluitTypeAdmin.list_display


class InformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = InformatieObjectType
    fields = InformatieObjectTypeAdmin.list_display
    fk_name = "catalogus"


@admin.register(Catalogus)
class CatalogusAdmin(
    ListObjectActionsAdminMixin, UUIDAdminMixin, CatalogusImportExportMixin, admin.ModelAdmin
):
    model = Catalogus
    change_list_template = "admin/catalogus_change_list.html"
    change_form_template = "admin/catalogi/change_form_catalogus.html"

    # List
    list_display = ("_admin_name", "domein", "rsin")
    list_filter = ("domein", "rsin")
    ordering = ("domein", "rsin")
    search_fields = (
        "uuid",
        "_admin_name",
        "domein",
        "rsin",
        "contactpersoon_beheer_naam",
    )

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("_admin_name", "domein", "rsin")}),
        (
            _("Contactpersoon beheer"),
            {
                "fields": (
                    "contactpersoon_beheer_naam",
                    "contactpersoon_beheer_telefoonnummer",
                    "contactpersoon_beheer_emailadres",
                )
            },
        ),
    )
    inlines = (ZaakTypeInline, BesluitTypeInline, InformatieObjectTypeInline)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="catalogi_catalogus_import",
            )
        ]
        return my_urls + urls

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(ZaakType, obj),
            link_to_related_objects(BesluitType, obj),
            link_to_related_objects(InformatieObjectType, obj),
        )
