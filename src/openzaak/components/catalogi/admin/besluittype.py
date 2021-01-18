# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import BesluitType
from .forms import BesluitTypeAdminForm
from .mixins import (
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    ReadOnlyPublishedMixin,
)


@admin.register(BesluitType)
class BesluitTypeAdmin(
    ReadOnlyPublishedMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    admin.ModelAdmin,
):
    # List
    list_display = ("omschrijving", "besluitcategorie", "catalogus", "is_published")
    list_filter = ("catalogus",)
    search_fields = ("uuid", "omschrijving", "besluitcategorie", "toelichting")
    ordering = ("catalogus", "omschrijving")
    raw_id_fields = (
        "catalogus",
        "zaaktypen",
        "informatieobjecttypen",
    )
    form = BesluitTypeAdminForm

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
                    "uuid",
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
    readonly_fields = ("uuid",)
