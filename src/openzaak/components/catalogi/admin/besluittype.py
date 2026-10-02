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
from .widgets import CatalogusFilterFKRawIdWidget


class BesluitTypeInformatieObjectTypeInline(admin.TabularInline):
    model = BesluitTypeInformatieObjectType
    extra = 0
    fields = ("_informatieobjecttype", "_iotype_base_url", "_iotype_relative_url")
    raw_id_fields = ("_informatieobjecttype", "_iotype_base_url")

    # published besluittypen are read-only
    def has_add_permission(self, request, obj=None):
        return (obj is None or obj.concept) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return (obj is None or obj.concept) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return (obj is None or obj.concept) and super().has_delete_permission(
            request, obj
        )

    def get_formset(self, request, obj=None, **kwargs):
        catalogus_pk = obj.catalogus_id if obj else request.GET.get("catalogus") or None
        admin_site = self.admin_site
        base_form = kwargs.pop("form", self.form)

        class CatalogusFilterForm(base_form):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                field = self.fields["_informatieobjecttype"]
                field.widget = CatalogusFilterFKRawIdWidget(
                    rel=BesluitTypeInformatieObjectType._meta.get_field(
                        "_informatieobjecttype"
                    ).remote_field,
                    admin_site=admin_site,
                    catalogus_pk=catalogus_pk,
                )

        return super().get_formset(request, obj, form=CatalogusFilterForm, **kwargs)


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
