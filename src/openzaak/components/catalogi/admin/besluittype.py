from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import BesluitType
from .mixins import ConceptAdminMixin, GeldigheidAdminMixin


@admin.register(BesluitType)
class BesluitTypeAdmin(GeldigheidAdminMixin, ConceptAdminMixin, admin.ModelAdmin):
    # List
    list_display = ("catalogus", "omschrijving", "besluitcategorie")

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "omschrijving",
                    "omschrijving_generiek",
                    "besluitcategorie",
                    "reactietermijn",
                    "toelichting",
                )
            },
        ),
        (
            _("Publicatie"),
            {
                "fields": (
                    "publicatie_indicatie",
                    "publicatietekst",
                    "publicatietermijn",
                )
            },
        ),
        (
            _("Relaties"),
            {
                "fields": (
                    "catalogus",
                    "informatieobjecttypen",
                    # 'resultaattypes',
                    "zaaktypen",
                )
            },
        ),
    )
    filter_horizontal = ("informatieobjecttypen", "zaaktypen")  # , 'resultaattypes'
