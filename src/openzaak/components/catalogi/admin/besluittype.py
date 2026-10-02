# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from openzaak.utils.admin import UUIDAdminMixin

from ..models import BesluitType, BesluitTypeInformatieObjectType
from .filters import GeldigheidFilter
from .forms import BesluitTypeAdminForm
from .mixins import (
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    GeldigheidPublishAdminMixin,
    ReadOnlyPublishedMixin,
    SideEffectsMixin,
)


class BesluitTypeInformatieObjectTypeInline(admin.TabularInline):
    model = BesluitTypeInformatieObjectType
    extra = 0
    fields = ("_informatieobjecttype", "_iotype_base_url", "_iotype_relative_url")
    raw_id_fields = ("_informatieobjecttype", "_iotype_base_url")


@admin.register(BesluitType)
class BesluitTypeAdmin(
    ReadOnlyPublishedMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    GeldigheidPublishAdminMixin,
    SideEffectsMixin,
    admin.ModelAdmin,
):
    # List
    list_display = ("omschrijving", "besluitcategorie", "catalogus", "is_published")
    list_filter = (
        GeldigheidFilter,
        "concept",
        "catalogus",
    )
    search_fields = ("uuid", "omschrijving", "besluitcategorie", "toelichting")
    ordering = ("catalogus", "omschrijving")
    raw_id_fields = (
        "catalogus",
        "zaaktypen",
    )
    form = BesluitTypeAdminForm
    inlines = (BesluitTypeInformatieObjectTypeInline,)

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
                    # 'resultaattypes',
                    "zaaktypen",
                )
            },
        ),
    )
    filter_horizontal = ("zaaktypen",)  # , 'resultaattypes'
    readonly_fields = ("uuid",)
