# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin

from openzaak.utils.admin import EditInlineAdminMixin

from ..models import (
    Adres,
    Buurt,
    Gemeente,
    GemeentelijkeOpenbareRuimte,
    Huishouden,
    Inrichtingselement,
    KadastraleOnroerendeZaak,
    Kunstwerkdeel,
    MaatschappelijkeActiviteit,
    OpenbareRuimte,
    Overige,
    Pand,
    Spoorbaandeel,
    Terreindeel,
    TerreinGebouwdObject,
    Waterdeel,
    Wegdeel,
    Wijk,
    Woonplaats,
    WozDeelobject,
    WozObject,
    WozWaarde,
    ZakelijkRecht,
    ZakelijkRechtHeeftAlsGerechtigde,
)


@admin.register(ZakelijkRechtHeeftAlsGerechtigde)
class ZakelijkRechtHeeftAlsGerechtigdeAdmin(admin.ModelAdmin):
    list_display = ("zakelijk_recht",)
    raw_id_fields = ("zakelijk_recht",)


class ZakelijkRechtHeeftAlsGerechtigdeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZakelijkRechtHeeftAlsGerechtigde
    fields = ZakelijkRechtHeeftAlsGerechtigdeAdmin.list_display


@admin.register(Adres)
class AdresAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie", "postcode")
    list_filter = ("wpl_woonplaats_naam",)
    search_fields = (
        "identificatie",
        "postcode",
        "locatie_omschrijving",
        "num_identificatie",
        "zaakobject_uuid",
    )
    ordering = ("identificatie",)
    raw_id_fields = (
        "zaakobject",
        "natuurlijkpersoon",
        "vestiging",
        "wozobject",
        "terreingebouwdobject",
    )


class AdresInline(EditInlineAdminMixin, admin.TabularInline):
    model = Adres
    fields = AdresAdmin.list_display


@admin.register(KadastraleOnroerendeZaak)
class KadastraleOnroerendeZaakAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "zakelijk_recht", "kadastrale_identificatie")
    search_fields = ("kadastrale_identificatie", "zaakobject_uuid")
    ordering = ("kadastrale_identificatie",)
    raw_id_fields = ("zaakobject", "zakelijk_recht")


class KadastraleOnroerendeZaakInline(EditInlineAdminMixin, admin.TabularInline):
    model = KadastraleOnroerendeZaak
    fields = KadastraleOnroerendeZaakAdmin.list_display


@admin.register(TerreinGebouwdObject)
class TerreinGebouwdObjectAdmin(admin.ModelAdmin):
    list_display = ("huishouden", "identificatie")
    search_fields = ("identificatie", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject", "huishouden")
    inlines = [AdresInline]


class TerreinGebouwdObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = TerreinGebouwdObject
    fields = TerreinGebouwdObjectAdmin.list_display


@admin.register(WozObject)
class WozObjectAdmin(admin.ModelAdmin):
    list_display = ("woz_deelobject", "woz_warde", "woz_object_nummer")
    search_fields = ("woz_object_nummer", "zaakobject_uuid")
    ordering = ("woz_object_nummer",)
    raw_id_fields = ("zaakobject", "woz_deelobject", "woz_warde")
    inlines = [AdresInline]


class WozObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = WozObject
    fields = WozObjectAdmin.list_display


@admin.register(Buurt)
class BuurtAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "buurt_code", "wyk_wijk_code")
    list_filter = ("gem_gemeente_code",)
    search_fields = ("buurt_code", "buurt_naam", "zaakobject_uuid")
    ordering = ("buurt_code",)
    raw_id_fields = ("zaakobject",)


class BuurtInline(EditInlineAdminMixin, admin.TabularInline):
    model = Buurt
    fields = BuurtAdmin.list_display


@admin.register(Gemeente)
class GemeenteAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "gemeente_code")
    search_fields = ("gemeente_code", "gemeente_naam", "zaakobject_uuid")
    ordering = ("gemeente_code",)
    raw_id_fields = ("zaakobject",)


class GemeenteInline(EditInlineAdminMixin, admin.TabularInline):
    model = Gemeente
    fields = GemeenteAdmin.list_display


@admin.register(GemeentelijkeOpenbareRuimte)
class GemeentelijkeOpenbareRuimteAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    search_fields = ("identificatie", "openbare_ruimte_naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class GemeentelijkeOpenbareRuimteInline(EditInlineAdminMixin, admin.TabularInline):
    model = GemeentelijkeOpenbareRuimte
    fields = GemeentelijkeOpenbareRuimteAdmin.list_display


@admin.register(Huishouden)
class HuishoudenAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "nummer")
    search_fields = ("nummer", "zaakobject_uuid")
    ordering = ("nummer",)
    raw_id_fields = ("zaakobject",)
    inlines = [TerreinGebouwdObjectInline]


class HuishoudenInline(EditInlineAdminMixin, admin.TabularInline):
    model = Huishouden
    fields = HuishoudenAdmin.list_display


@admin.register(Inrichtingselement)
class InrichtingselementAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class InrichtingselementInline(EditInlineAdminMixin, admin.TabularInline):
    model = Inrichtingselement
    fields = InrichtingselementAdmin.list_display


@admin.register(Kunstwerkdeel)
class KunstwerkdeelAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class KunstwerkdeelInline(EditInlineAdminMixin, admin.TabularInline):
    model = Kunstwerkdeel
    fields = KunstwerkdeelAdmin.list_display


@admin.register(MaatschappelijkeActiviteit)
class MaatschappelijkeActiviteitAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "kvk_nummer")
    search_fields = ("kvk_nummer", "handelsnaam", "zaakobject_uuid")
    ordering = ("kvk_nummer",)
    raw_id_fields = ("zaakobject",)


class MaatschappelijkeActiviteitInline(EditInlineAdminMixin, admin.TabularInline):
    model = MaatschappelijkeActiviteit
    fields = MaatschappelijkeActiviteitAdmin.list_display


@admin.register(OpenbareRuimte)
class OpenbareRuimteAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    search_fields = ("identificatie", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class OpenbareRuimteInline(EditInlineAdminMixin, admin.TabularInline):
    model = OpenbareRuimte
    fields = OpenbareRuimteAdmin.list_display


@admin.register(Overige)
class OverigeAdmin(admin.ModelAdmin):
    list_display = ("zaakobject",)
    search_fields = ("zaakobject", "zaakobject_uuid")
    ordering = ("zaakobject",)
    raw_id_fields = ("zaakobject",)


class OverigeInline(EditInlineAdminMixin, admin.TabularInline):
    model = Overige
    fields = OverigeAdmin.list_display


@admin.register(Pand)
class PandAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    search_fields = ("identificatie", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class PandInline(EditInlineAdminMixin, admin.TabularInline):
    model = Pand
    fields = PandAdmin.list_display


@admin.register(Spoorbaandeel)
class SpoorbaandeelAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class SpoorbaandeelInline(EditInlineAdminMixin, admin.TabularInline):
    model = Spoorbaandeel
    fields = SpoorbaandeelAdmin.list_display


@admin.register(Terreindeel)
class TerreindeelAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class TerreindeelInline(EditInlineAdminMixin, admin.TabularInline):
    model = Terreindeel
    fields = TerreindeelAdmin.list_display


@admin.register(Waterdeel)
class WaterdeelAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type_waterdeel",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class WaterdeelInline(EditInlineAdminMixin, admin.TabularInline):
    model = Waterdeel
    fields = WaterdeelAdmin.list_display


@admin.register(Wegdeel)
class WegdeelAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    list_filter = ("type",)
    search_fields = ("identificatie", "naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class WegdeelInline(EditInlineAdminMixin, admin.TabularInline):
    model = Wegdeel
    fields = WegdeelAdmin.list_display


@admin.register(Wijk)
class WijkAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "wijk_code")
    search_fields = ("wijk_code", "wijk_naam", "zaakobject_uuid")
    ordering = ("wijk_code",)
    raw_id_fields = ("zaakobject",)


class WijkInline(EditInlineAdminMixin, admin.TabularInline):
    model = Wijk
    fields = WijkAdmin.list_display


@admin.register(Woonplaats)
class WoonplaatsAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    search_fields = ("identificatie", "woonplaats_naam", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)


class WoonplaatsInline(EditInlineAdminMixin, admin.TabularInline):
    model = Woonplaats
    fields = WoonplaatsAdmin.list_display


@admin.register(WozDeelobject)
class WozDeelobjectAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "nummer_woz_deel_object")
    search_fields = ("nummer_woz_deel_object", "zaakobject_uuid")
    ordering = ("nummer_woz_deel_object",)
    raw_id_fields = ("zaakobject",)
    inlines = [WozObjectInline]


class WozDeelobjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = WozDeelobject
    fields = WozDeelobjectAdmin.list_display


@admin.register(WozWaarde)
class WozWaardeAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "waardepeildatum")
    search_fields = ("waardepeildatum", "zaakobject_uuid")
    ordering = ("waardepeildatum",)
    raw_id_fields = ("zaakobject",)
    inlines = [WozObjectInline]


class WozWaardeInline(EditInlineAdminMixin, admin.TabularInline):
    model = WozWaarde
    fields = WozWaardeAdmin.list_display


@admin.register(ZakelijkRecht)
class ZakelijkRechtAdmin(admin.ModelAdmin):
    list_display = ("zaakobject", "identificatie")
    search_fields = ("identificatie", "zaakobject_uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("zaakobject",)
    inlines = [ZakelijkRechtHeeftAlsGerechtigdeInline, KadastraleOnroerendeZaakInline]


class ZakelijkRechtInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZakelijkRecht
    fields = ZakelijkRechtAdmin.list_display
