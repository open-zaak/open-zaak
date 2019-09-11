from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import Eigenschap, EigenschapSpecificatie
from .mixins import FilterSearchOrderingAdminMixin


@admin.register(Eigenschap)
class EigenschapAdmin(FilterSearchOrderingAdminMixin, admin.ModelAdmin):
    model = Eigenschap

    # List
    list_display = ("eigenschapnaam", "zaaktype")

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("eigenschapnaam", "definitie", "toelichting")}),
        (
            _("Relaties"),
            {
                "fields": (
                    "zaaktype",
                    "specificatie_van_eigenschap",
                    "referentie_naar_eigenschap",
                )
            },
        ),
    )


@admin.register(EigenschapSpecificatie)
class EigenschapSpecificatieAdmin(admin.ModelAdmin):
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
