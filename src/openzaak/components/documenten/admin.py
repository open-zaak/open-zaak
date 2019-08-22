from django.contrib import admin

from privates.admin import PrivateMediaMixin

from .models import (
    EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten, ObjectInformatieObject
)


class GebruiksrechtenInline(admin.TabularInline):
    model = Gebruiksrechten
    extra = 1


class EnkelvoudigInformatieObjectInline(admin.StackedInline):
    model = EnkelvoudigInformatieObject
    extra = 1


def unlock(modeladmin, request, queryset):
    queryset.update(lock="")


@admin.register(EnkelvoudigInformatieObjectCanonical)
class EnkelvoudigInformatieObjectCanonicalAdmin(PrivateMediaMixin, admin.ModelAdmin):
    list_display = ["__str__", "get_not_lock_display"]
    inlines = [EnkelvoudigInformatieObjectInline, GebruiksrechtenInline]
    private_media_fields = ("inhoud",)
    actions = [unlock]

    def get_not_lock_display(self, obj) -> bool:
        return not bool(obj.lock)

    get_not_lock_display.short_description = "free to change"
    get_not_lock_display.boolean = True


@admin.register(EnkelvoudigInformatieObject)
class EnkelvoudigInformatieObjectAdmin(admin.ModelAdmin):
    list_display = ("identificatie", "uuid", "bronorganisatie", "titel", "versie")
    list_filter = ("bronorganisatie",)
    search_fields = ("identificatie", "uuid")
    ordering = ("-begin_registratie",)
    raw_id_fields = ("canonical",)


@admin.register(Gebruiksrechten)
class GebruiksrechtenAdmin(admin.ModelAdmin):
    list_display = ("uuid", "informatieobject")
    list_filter = ("informatieobject",)
    raw_id_fields = ("informatieobject",)


@admin.register(ObjectInformatieObject)
class ObjectInformatieObjectAdmin(admin.ModelAdmin):
    list_display = ("uuid", "informatieobject", "object_type", "object")
    list_select_related = ("zaak", "besluit")
    raw_id_fields = ("informatieobject", "zaak", "besluit")
    readonly_fields = ("uuid",)
