from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .mixins import CatalogusContextAdminMixin
from ..models import StatusType


@admin.register(StatusType)
class StatusTypeAdmin(CatalogusContextAdminMixin, admin.ModelAdmin):
    model = StatusType

    # List
    list_display = ("statustype_omschrijving", "statustypevolgnummer", "zaaktype")
    list_filter = ("zaaktype", "informeren")
    search_fields = (
        "statustype_omschrijving",
        "statustype_omschrijving_generiek",
        "statustypevolgnummer",
    )
    ordering = ("zaaktype", "statustypevolgnummer")

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "statustype_omschrijving",
                    "statustype_omschrijving_generiek",
                    "statustypevolgnummer",
                    "informeren",
                    "statustekst",
                    "toelichting",
                )
            },
        ),
        (_("Relaties"), {"fields": ("zaaktype",)}),
    )
    raw_id_fields = ("zaaktype",)
