from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from privates.admin import PrivateMediaMixin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    UUIDAdminMixin,
)

from .api import viewsets
from .models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)


class GebruiksrechtenInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Gebruiksrechten
    readonly_fields = ("uuid",)
    extra = 1
    viewset = viewsets.GebruiksrechtenViewSet


class EnkelvoudigInformatieObjectInline(
    AuditTrailInlineAdminMixin, admin.StackedInline
):
    model = EnkelvoudigInformatieObject
    raw_id_fields = ("canonical", "_informatieobjecttype")
    readonly_fields = ("uuid",)
    extra = 1
    verbose_name = _("versie")
    verbose_name_plural = _("versies")
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet


def unlock(modeladmin, request, queryset):
    queryset.update(lock="")


@admin.register(EnkelvoudigInformatieObjectCanonical)
class EnkelvoudigInformatieObjectCanonicalAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["__str__", "get_not_lock_display"]
    inlines = [EnkelvoudigInformatieObjectInline, GebruiksrechtenInline]
    actions = [unlock]

    def get_not_lock_display(self, obj) -> bool:
        return not bool(obj.lock)

    get_not_lock_display.short_description = "free to change"
    get_not_lock_display.boolean = True

    def get_viewset(self, request):
        return None


@admin.register(EnkelvoudigInformatieObject)
class EnkelvoudigInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, PrivateMediaMixin, admin.ModelAdmin
):
    list_display = (
        "identificatie",
        "uuid",
        "bronorganisatie",
        "creatiedatum",
        "titel",
        "versie",
        "_locked",
    )
    list_filter = ("bronorganisatie",)
    search_fields = ("identificatie", "uuid")
    ordering = ("-begin_registratie",)
    date_hierarchy = "creatiedatum"
    raw_id_fields = ("canonical", "_informatieobjecttype")
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet
    private_media_fields = ("inhoud",)

    def _locked(self, obj) -> bool:
        return obj.locked

    _locked.boolean = True
    _locked.short_description = _("locked")


@admin.register(Gebruiksrechten)
class GebruiksrechtenAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ("uuid", "informatieobject")
    list_filter = ("informatieobject",)
    raw_id_fields = ("informatieobject",)
    viewset = viewsets.GebruiksrechtenViewSet


@admin.register(ObjectInformatieObject)
class ObjectInformatieObjectAdmin(admin.ModelAdmin):
    list_display = ("uuid", "informatieobject", "object_type", "object")
    list_select_related = ("_zaak", "_besluit")
    raw_id_fields = ("informatieobject", "_zaak", "_besluit")
    readonly_fields = ("uuid",)
