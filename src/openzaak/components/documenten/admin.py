from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from privates.admin import PrivateMediaMixin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from .api import viewsets
from .models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)


@admin.register(Gebruiksrechten)
class GebruiksrechtenAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("informatieobject", "startdatum", "einddatum")
    list_filter = ("informatieobject", "startdatum", "einddatum")
    search_fields = ("uuid", "informatieobject", "omschrijving_voorwaarden")
    ordering = ("startdatum", "informatieobject")
    raw_id_fields = ("informatieobject",)
    viewset = viewsets.GebruiksrechtenViewSet


@admin.register(ObjectInformatieObject)
class ObjectInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    list_display = ("informatieobject", "object_type", "zaak", "besluit")
    list_filter = ("object_type",)
    list_select_related = ("zaak", "besluit")
    search_fields = ("uuid", "zaak", "besluit")
    ordering = ("informatieobject",)
    raw_id_fields = ("informatieobject", "zaak", "besluit")
    viewset = viewsets.ObjectInformatieObject


class GebruiksrechtenInline(EditInlineAdminMixin, admin.TabularInline):
    model = Gebruiksrechten
    fields = GebruiksrechtenAdmin.list_display


class ObjectInformatieObjectInline(
    AuditTrailAdminMixin, EditInlineAdminMixin, admin.TabularInline
):
    model = ObjectInformatieObject
    fields = ObjectInformatieObjectAdmin.list_display


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
    inlines = [
        EnkelvoudigInformatieObjectInline,
        GebruiksrechtenInline,
        ObjectInformatieObjectInline,
    ]
    actions = [unlock]

    def get_not_lock_display(self, obj) -> bool:
        return not bool(obj.lock)

    get_not_lock_display.short_description = "free to change"
    get_not_lock_display.boolean = True

    def get_viewset(self, request):
        return None


@admin.register(EnkelvoudigInformatieObject)
class EnkelvoudigInformatieObjectAdmin(
    AuditTrailAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    PrivateMediaMixin,
    admin.ModelAdmin,
):
    list_display = (
        "identificatie",
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
    readonly_fields = ("uuid",)

    def _locked(self, obj) -> bool:
        return obj.locked

    _locked.boolean = True
    _locked.short_description = _("locked")

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(Gebruiksrechten, obj.canonical),
            link_to_related_objects(ObjectInformatieObject, obj.canonical),
        )
