# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import DynamicArrayMixin, UUIDAdminMixin

from ..models import Eigenschap, EigenschapSpecificatie
from .mixins import CatalogusContextAdminMixin, ReadOnlyPublishedZaaktypeMixin


@admin.register(Eigenschap)
class EigenschapAdmin(
    ReadOnlyPublishedZaaktypeMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = Eigenschap

    # List
    list_display = ("eigenschapnaam", "zaaktype")
    list_filter = ("zaaktype", "eigenschapnaam")
    ordering = ("zaaktype", "eigenschapnaam")
    search_fields = ("uuid", "eigenschapnaam", "definitie", "toelichting")
    raw_id_fields = ("zaaktype", "specificatie_van_eigenschap")

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("eigenschapnaam", "definitie", "toelichting", "uuid",)},
        ),
        (_("Relaties"), {"fields": ("zaaktype", "specificatie_van_eigenschap",)},),
    )
    readonly_fields = ("uuid",)


@admin.register(EigenschapSpecificatie)
class EigenschapSpecificatieAdmin(
    DynamicArrayMixin, CatalogusContextAdminMixin, admin.ModelAdmin
):
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
