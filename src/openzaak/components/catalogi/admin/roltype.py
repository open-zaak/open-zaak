from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import RolType
from .mixins import CatalogusContextAdminMixin


@admin.register(RolType)
class RolTypeAdmin(CatalogusContextAdminMixin, admin.ModelAdmin):
    model = RolType

    # List
    list_display = ("omschrijving", "zaaktype", "uuid")
    list_filter = ("zaaktype", "omschrijving_generiek")
    search_fields = ("omschrijving",)

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("omschrijving", "omschrijving_generiek")},),
        (_("Relaties"), {"fields": ("zaaktype",)}),
    )
    raw_id_fields = ("zaaktype",)
