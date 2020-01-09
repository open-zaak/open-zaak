from django.contrib import admin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    EditInlineAdminMixin,
    UUIDAdminMixin,
)

from .models import Besluit, BesluitInformatieObject


@admin.register(BesluitInformatieObject)
class BesluitInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    list_display = ("besluit", "_informatieobject", "_informatieobject_url")
    list_filter = ("besluit",)
    search_fields = ("besluit", "_informatieobject", "_informatieobject_url")
    ordering = ("besluit", "_informatieobject", "_informatieobject_url")
    raw_id_fields = ("besluit", "_informatieobject")
    viewset = (
        "openzaak.components.besluiten.api.viewsets.BesluitInformatieObjectViewSet"
    )


class BesluitInformatieObjectInline(
    AuditTrailInlineAdminMixin, EditInlineAdminMixin, admin.TabularInline
):
    model = BesluitInformatieObject
    fields = BesluitInformatieObjectAdmin.list_display
    viewset = (
        "openzaak.components.besluiten.api.viewsets.BesluitInformatieObjectViewSet"
    )


@admin.register(Besluit)
class BesluitAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("verantwoordelijke_organisatie", "identificatie", "datum")
    list_filter = ("datum", "ingangsdatum")
    date_hierarchy = "datum"
    search_fields = (
        "verantwoordelijke_organisatie",
        "identificatie",
        "uuid",
    )
    ordering = ("datum", "identificatie")
    raw_id_fields = ("_besluittype", "_zaak")
    inlines = (BesluitInformatieObjectInline,)
    viewset = "openzaak.components.besluiten.api.viewsets.BesluitViewSet"
