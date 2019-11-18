from django.contrib import admin
from openzaak.utils.admin import AuditTrailAdminMixin

from .models import Besluit, BesluitInformatieObject


class BesluitInformatieObjectInline(admin.TabularInline):
    model = BesluitInformatieObject
    extra = 0
    readonly_fields = ("uuid",)


@admin.register(Besluit)
class BesluitAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ("verantwoordelijke_organisatie", "identificatie", "datum")
    list_filter = ("datum", "ingangsdatum")
    date_hierarchy = "datum"
    search_fields = (
        "verantwoordelijke_organisatie",
        "identificatie",
        "besluittype",
        "zaak",
    )
    inlines = (BesluitInformatieObjectInline,)
    viewset = "openzaak.components.besluiten.api.viewsets.BesluitViewSet"


@admin.register(BesluitInformatieObject)
class BesluitInformatieObjectAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ("besluit", "informatieobject")
    viewset = "openzaak.components.besluiten.api.viewsets.BesluitInformatieObjectViewSet"
