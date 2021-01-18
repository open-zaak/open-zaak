# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import RolType
from .mixins import CatalogusContextAdminMixin, ReadOnlyPublishedZaaktypeMixin


@admin.register(RolType)
class RolTypeAdmin(
    ReadOnlyPublishedZaaktypeMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = RolType

    # List
    list_display = ("omschrijving", "zaaktype")
    list_filter = ("zaaktype", "omschrijving_generiek")
    search_fields = (
        "uuid",
        "omschrijving",
    )

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("omschrijving", "omschrijving_generiek", "uuid",)},
        ),
        (_("Relaties"), {"fields": ("zaaktype",)}),
    )
    raw_id_fields = ("zaaktype",)
    readonly_fields = ("uuid",)
