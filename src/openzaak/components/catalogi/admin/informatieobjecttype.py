from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import InformatieObjectType, ZaakTypeInformatieObjectType
from .mixins import CatalogusContextAdminMixin, GeldigheidAdminMixin, PublishAdminMixin


class ZaakTypeInformatieObjectTypeInline(admin.TabularInline):
    model = ZaakTypeInformatieObjectType
    extra = 1
    raw_id_fields = ("zaaktype", "statustype")
    readonly_fields = ("uuid",)


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
