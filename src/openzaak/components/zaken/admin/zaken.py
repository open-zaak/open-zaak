from django.contrib import admin

from openzaak.components.zaken.api import viewsets
from openzaak.utils.admin import AuditTrailAdminMixin, AuditTrailInlineAdminMixin

from ..models import (
    KlantContact,
    RelevanteZaakRelatie,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)


class StatusInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Status
    viewset = viewsets.StatusViewSet


class ZaakObjectInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakObject
    viewset = viewsets.ZaakObjectViewSet


class ZaakEigenschapInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakEigenschap
    viewset = viewsets.ZaakEigenschapViewSet


class ZaakInformatieObjectInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakInformatieObject
    viewset = viewsets.ZaakInformatieObjectViewSet


class KlantContactInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = KlantContact
    viewset = viewsets.KlantContactViewSet


class RolInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Rol
    raw_id_fields = ["zaak"]
    viewset = viewsets.RolViewSet


class ResultaatInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Resultaat
    viewset = viewsets.ResultaatViewSet


class RelevanteZaakRelatieInline(admin.TabularInline):
    model = RelevanteZaakRelatie
    fk_name = "zaak"


@admin.register(Zaak)
class ZaakAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["identificatie"]
    inlines = [
        StatusInline,
        ZaakObjectInline,
        ZaakInformatieObjectInline,
        KlantContactInline,
        ZaakEigenschapInline,
        RolInline,
        ResultaatInline,
        RelevanteZaakRelatieInline,
    ]
    raw_id_fields = ["zaaktype", "hoofdzaak"]
    viewset = viewsets.ZaakViewSet


@admin.register(Status)
class StatusAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "datum_status_gezet"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.StatusViewSet


@admin.register(ZaakObject)
class ZaakObjectAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "object", "relatieomschrijving"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.ZaakObjectViewSet


@admin.register(KlantContact)
class KlantContactAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "identificatie", "datumtijd", "kanaal"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.KlantContactViewSet


@admin.register(ZaakEigenschap)
class ZaakEigenschapAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "eigenschap", "waarde"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.ZaakEigenschapViewSet


@admin.register(ZaakInformatieObject)
class ZaakInformatieObjectAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "_informatieobject", "_informatieobject_url"]
    list_select_related = ["zaak", "_informatieobject"]
    raw_id_fields = ["zaak", "_informatieobject"]
    viewset = viewsets.ZaakInformatieObjectViewSet


@admin.register(Resultaat)
class ResultaatAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "toelichting"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.ResultaatViewSet


@admin.register(Rol)
class RolAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "betrokkene", "betrokkene_type"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = viewsets.RolViewSet
