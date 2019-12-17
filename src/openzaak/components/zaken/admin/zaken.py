from django.contrib import admin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    UUIDAdminMixin,
)

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
    raw_id_fields = ("statustype",)
    viewset = "openzaak.components.zaken.api.viewsets.StatusViewSet"


class ZaakObjectInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakObject
    viewset = "openzaak.components.zaken.api.viewsets.ZaakObjectViewSet"


class ZaakEigenschapInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakEigenschap
    raw_id_fields = ("eigenschap",)
    viewset = "openzaak.components.zaken.api.viewsets.ZaakEigenschapViewSet"


class ZaakInformatieObjectInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = ZaakInformatieObject
    raw_id_fields = ("_informatieobject",)
    viewset = "openzaak.components.zaken.api.viewsets.ZaakInformatieObjectViewSet"


class KlantContactInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = KlantContact
    viewset = "openzaak.components.zaken.api.viewsets.KlantContactViewSet"


class RolInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Rol
    raw_id_fields = ("zaak", "roltype")
    viewset = "openzaak.components.zaken.api.viewsets.RolViewSet"


class ResultaatInline(AuditTrailInlineAdminMixin, admin.TabularInline):
    model = Resultaat
    raw_id_fields = ("resultaattype",)
    viewset = "openzaak.components.zaken.api.viewsets.ResultaatViewSet"


class RelevanteZaakRelatieInline(admin.TabularInline):
    model = RelevanteZaakRelatie
    fk_name = "zaak"
    raw_id_fields = ("_relevant_zaak",)


@admin.register(Zaak)
class ZaakAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = (
        "identificatie",
        "registratiedatum",
        "startdatum",
        "einddatum",
        "archiefstatus",
    )
    search_fields = (
        "identificatie",
        "uuid",
    )
    date_hierarchy = "registratiedatum"
    list_filter = ("startdatum", "archiefstatus", "vertrouwelijkheidaanduiding")
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
    raw_id_fields = ["_zaaktype", "hoofdzaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakViewSet"


@admin.register(Status)
class StatusAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "datum_status_gezet"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.StatusViewSet"


@admin.register(ZaakObject)
class ZaakObjectAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "object", "relatieomschrijving"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakObjectViewSet"


@admin.register(KlantContact)
class KlantContactAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "identificatie", "datumtijd", "kanaal"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.KlantContactViewSet"


@admin.register(ZaakEigenschap)
class ZaakEigenschapAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "eigenschap", "waarde"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakEigenschapViewSet"


@admin.register(ZaakInformatieObject)
class ZaakInformatieObjectAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "_informatieobject", "_informatieobject_url"]
    list_select_related = ["zaak", "_informatieobject"]
    raw_id_fields = ["zaak", "_informatieobject"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakInformatieObjectViewSet"


@admin.register(Resultaat)
class ResultaatAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "toelichting"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ResultaatViewSet"


@admin.register(Rol)
class RolAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "betrokkene", "betrokkene_type"]
    list_select_related = ["zaak"]
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.RolViewSet"
