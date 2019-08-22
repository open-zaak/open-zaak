from django.contrib import admin

from .models import Besluit, BesluitInformatieObject


class BesluitInformatieObjectInline(admin.TabularInline):
    model = BesluitInformatieObject
    extra = 0
    readonly_fields = ("uuid",)


@admin.register(Besluit)
class BesluitAdmin(admin.ModelAdmin):
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
