from django.contrib import admin

from openzaak.components.zaken.api.viewsets import StatusViewSet
from openzaak.utils.admin import AuditTrailAdminMixin

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


class StatusInline(admin.TabularInline):
    model = Status


class ZaakObjectInline(admin.TabularInline):
    model = ZaakObject


class ZaakEigenschapInline(admin.TabularInline):
    model = ZaakEigenschap


class ZaakInformatieObjectInline(admin.TabularInline):
    model = ZaakInformatieObject


class KlantContactInline(admin.TabularInline):
    model = KlantContact


class RolInline(admin.TabularInline):
    model = Rol
    raw_id_fields = ["zaak"]


class ResultaatInline(admin.TabularInline):
    model = Resultaat


class RelevanteZaakRelatieInline(admin.TabularInline):
    model = RelevanteZaakRelatie
    fk_name = "zaak"


@admin.register(Zaak)
class ZaakAdmin(admin.ModelAdmin):
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


@admin.register(Status)
class StatusAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "datum_status_gezet"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = StatusViewSet


@admin.register(ZaakObject)
class ZaakObjectAdmin(admin.ModelAdmin):
    list_display = ["zaak", "object", "relatieomschrijving"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]


@admin.register(KlantContact)
class KlantContactAdmin(admin.ModelAdmin):
    list_display = ["zaak", "identificatie", "datumtijd", "kanaal"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]


@admin.register(ZaakEigenschap)
class ZaakEigenschapAdmin(admin.ModelAdmin):
    list_display = ["zaak", "eigenschap", "waarde"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]


@admin.register(ZaakInformatieObject)
class ZaakInformatieObjectAdmin(admin.ModelAdmin):
    list_display = ["zaak", "_informatieobject", "_informatieobject_url"]
    list_select_related = ["zaak", "_informatieobject"]
    raw_id_fields = ["zaak", "_informatieobject"]


@admin.register(Resultaat)
class ResultaatAdmin(admin.ModelAdmin):
    list_display = ["zaak", "toelichting"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
