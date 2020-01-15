from django.contrib import admin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from .models import Besluit, BesluitInformatieObject


@admin.register(BesluitInformatieObject)
class BesluitInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    list_display = ("besluit", "_informatieobject", "_informatieobject_url")
    list_filter = ("besluit",)
    search_fields = (
        "besluit__uuid",
        "_informatieobject__enkelvoudiginformatieobject__uuid",
        "_informatieobject_url",
    )
    ordering = ("besluit", "_informatieobject", "_informatieobject_url")
    raw_id_fields = ("besluit", "_informatieobject")
    viewset = (
        "openzaak.components.besluiten.api.viewsets.BesluitInformatieObjectViewSet"
    )


class BesluitInformatieObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitInformatieObject
    fields = BesluitInformatieObjectAdmin.list_display
    fk_name = "besluit"


@admin.register(Besluit)
class BesluitAdmin(
    AuditTrailAdminMixin, ListObjectActionsAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
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

    def get_object_actions(self, obj):
        return (link_to_related_objects(BesluitInformatieObject, obj),)
