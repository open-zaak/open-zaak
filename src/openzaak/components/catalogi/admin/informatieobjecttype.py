from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import InformatieObjectType, ZaakTypeInformatieObjectType
from .mixins import GeldigheidAdminMixin, PublishAdminMixin


class ZaakTypeInformatieObjectTypeInline(admin.TabularInline):
    model = ZaakTypeInformatieObjectType
    extra = 1
    raw_id_fields = ("zaaktype", "statustype")


@admin.register(InformatieObjectType)
class InformatieObjectTypeAdmin(
    GeldigheidAdminMixin, PublishAdminMixin, admin.ModelAdmin
):
    list_display = ("catalogus", "omschrijving")
    list_filter = ("catalogus",)
    search_fields = ("omschrijving", "trefwoord", "toelichting")
    ordering = ("catalogus", "omschrijving")

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("omschrijving", "vertrouwelijkheidaanduiding",)},),
        (_("Relaties"), {"fields": ("catalogus",)}),
    )
    inlines = (ZaakTypeInformatieObjectTypeInline,)  # zaaktypes
