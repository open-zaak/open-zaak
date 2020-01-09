from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import EditInlineAdminMixin, UUIDAdminMixin

from ..models import InformatieObjectType, ZaakTypeInformatieObjectType
from .mixins import CatalogusContextAdminMixin, GeldigheidAdminMixin, PublishAdminMixin


@admin.register(ZaakTypeInformatieObjectType)
class ZaakTypeInformatieObjectTypeAdmin(UUIDAdminMixin, admin.ModelAdmin):
    model = ZaakTypeInformatieObjectType

    # List
    list_display = ("zaaktype", "informatieobjecttype", "statustype", "volgnummer")
    list_filter = (
        "zaaktype",
        "informatieobjecttype",
        "richting",
    )
    search_fields = ("uuid", "volgnummer")
    ordering = ("zaaktype", "informatieobjecttype", "volgnummer")

    # Detail
    fieldsets = (
        (_("Algemeen"), {"fields": ("volgnummer", "richting",)},),
        (_("Relaties"), {"fields": ("zaaktype", "informatieobjecttype", "statustype")}),
    )
    raw_id_fields = ("zaaktype", "informatieobjecttype", "statustype")


class ZaakTypeInformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakTypeInformatieObjectType
    fields = ZaakTypeInformatieObjectTypeAdmin.list_display


@admin.register(InformatieObjectType)
class InformatieObjectTypeAdmin(
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    admin.ModelAdmin,
):
    list_display = ("omschrijving", "catalogus", "is_published")
    list_filter = ("catalogus",)
    search_fields = ("uuid", "omschrijving", "trefwoord", "toelichting")
    ordering = ("catalogus", "omschrijving")
    raw_id_fields = ("catalogus",)

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("omschrijving", "vertrouwelijkheidaanduiding", "uuid",)},
        ),
        (_("Relaties"), {"fields": ("catalogus",)}),
    )
    inlines = (ZaakTypeInformatieObjectTypeInline,)  # zaaktypes
    readonly_fields = ("uuid",)
