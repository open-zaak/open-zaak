# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..models import InformatieObjectType, ZaakTypeInformatieObjectType
from .forms import ZaakTypeInformatieObjectTypeAdminForm
from .mixins import (
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    ReadOnlyPublishedMixin,
    ReadOnlyPublishedParentMixin,
)


@admin.register(ZaakTypeInformatieObjectType)
class ZaakTypeInformatieObjectTypeAdmin(
    CatalogusContextAdminMixin,
    ReadOnlyPublishedParentMixin,
    UUIDAdminMixin,
    admin.ModelAdmin,
):
    model = ZaakTypeInformatieObjectType
    form = ZaakTypeInformatieObjectTypeAdminForm

    # List
    list_display = ("zaaktype", "informatieobjecttype", "statustype", "volgnummer")
    list_filter = (
        "zaaktype",
        "informatieobjecttype",
        "richting",
    )
    search_fields = (
        "uuid",
        "volgnummer",
        "zaaktype__uuid",
        "informatieobjecttype__uuid",
    )
    ordering = ("zaaktype", "informatieobjecttype", "volgnummer")

    # Detail
    fieldsets = (
        (_("Algemeen"), {"fields": ("volgnummer", "richting",)},),
        (_("Relaties"), {"fields": ("zaaktype", "informatieobjecttype", "statustype")}),
    )
    raw_id_fields = ("zaaktype", "informatieobjecttype", "statustype")

    def get_concept(self, obj):
        if not obj:
            return True
        return obj.zaaktype.concept or obj.informatieobjecttype.concept


class ZaakTypeInformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakTypeInformatieObjectType
    fields = ZaakTypeInformatieObjectTypeAdmin.list_display


@admin.register(InformatieObjectType)
class InformatieObjectTypeAdmin(
    ReadOnlyPublishedMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "omschrijving",
        "catalogus",
        "vertrouwelijkheidaanduiding",
        "num_zaaktypen",
        "is_published",
    )
    list_filter = ("catalogus", "concept", "vertrouwelijkheidaanduiding")
    search_fields = (
        "uuid",
        "omschrijving",
    )
    ordering = ("catalogus", "omschrijving")
    raw_id_fields = ("catalogus",)

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("omschrijving", "vertrouwelijkheidaanduiding", "uuid",)},
        ),
        (_("Relaties"), {"fields": ("catalogus",)}),
    )
    inlines = (ZaakTypeInformatieObjectTypeInline,)  # zaaktypes

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(num_zaaktypen=Count("zaaktypen"))

    def get_object_actions(self, obj):
        return (link_to_related_objects(ZaakTypeInformatieObjectType, obj),)

    def num_zaaktypen(self, obj) -> int:
        return obj.num_zaaktypen

    num_zaaktypen.short_description = _("# zaaktypen")
