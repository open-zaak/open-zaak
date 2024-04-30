# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import CheckListItem, StatusType
from .mixins import CatalogusContextAdminMixin, ReadOnlyPublishedZaaktypeMixin


class ChecklistItemInline(admin.TabularInline):
    model = CheckListItem
    fields = (
        "itemnaam",
        "vraagstelling",
        "verplicht",
        "toelichting",
    )
    extra = 1


@admin.register(StatusType)
class StatusTypeAdmin(
    ReadOnlyPublishedZaaktypeMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = StatusType

    # List
    list_display = ("statustype_omschrijving", "statustypevolgnummer", "zaaktype")
    list_filter = ("zaaktype", "informeren")
    search_fields = (
        "uuid",
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
                    "datum_begin_geldigheid",
                    "datum_einde_geldigheid",
                )
            },
        ),
        (_("Relaties"), {"fields": ("zaaktype",)}),
    )
    inlines = [ChecklistItemInline]
    raw_id_fields = ("zaaktype",)
    readonly_fields = ("uuid",)
