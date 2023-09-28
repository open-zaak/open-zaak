# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import ZaakObjectType
from .mixins import ReadOnlyPublishedZaaktypeMixin


@admin.register(ZaakObjectType)
class ZaakObjectTypeAdmin(
    ReadOnlyPublishedZaaktypeMixin, UUIDAdminMixin, admin.ModelAdmin,
):
    # List
    list_display = (
        "zaaktype",
        "ander_objecttype",
    )
    list_filter = ("zaaktype", "ander_objecttype")
    search_fields = ("uuid", "relatie_omschrijving")
    ordering = ("zaaktype", "relatie_omschrijving")

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("ander_objecttype", "objecttype", "relatie_omschrijving",)},
        ),
        (_("Relaties"), {"fields": ("zaaktype",)}),
    )
    raw_id_fields = ("zaaktype",)
