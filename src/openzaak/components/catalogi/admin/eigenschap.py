from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import Eigenschap, EigenschapSpecificatie
from .mixins import CatalogusContextAdminMixin


@admin.register(Eigenschap)
class EigenschapAdmin(UUIDAdminMixin, CatalogusContextAdminMixin, admin.ModelAdmin):
    model = Eigenschap

    # List
    list_display = ("eigenschapnaam", "zaaktype")
    list_filter = ("zaaktype", "eigenschapnaam")
    ordering = ("zaaktype", "eigenschapnaam")
    search_fields = ("uuid", "eigenschapnaam", "definitie", "toelichting")

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("eigenschapnaam", "definitie", "toelichting")}),
        (_("Relaties"), {"fields": ("zaaktype", "specificatie_van_eigenschap",)},),
    )


@admin.register(EigenschapSpecificatie)
class EigenschapSpecificatieAdmin(CatalogusContextAdminMixin, admin.ModelAdmin):
    # List
    list_display = ("groep", "formaat", "lengte", "kardinaliteit")  # Add is_van
    # list_filter = ('rsin', )  # Add is_van
    search_fields = ("groep",)

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "groep",
                    "formaat",
                    "lengte",
                    "kardinaliteit",
                    "waardenverzameling",
                )
            },
        ),
    )
