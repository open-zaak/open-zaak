from django.contrib import admin

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


@admin.register(Adres)
class AdresAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Buurt)
class BuurtAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "buurt_code", "wyk_wijk_code"]


@admin.register(Gemeente)
class GemeenteAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "gemeente_code"]


@admin.register(GemeentelijkeOpenbareRuimte)
class GemeentelijkeOpenbareRuimteAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Huishouden)
class HuishoudenAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "nummer"]


@admin.register(Inrichtingselement)
class InrichtingselementAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Kunstwerkdeel)
class KunstwerkdeelAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(MaatschappelijkeActiviteit)
class MaatschappelijkeActiviteitAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "kvk_nummer"]


@admin.register(OpenbareRuimte)
class OpenbareRuimteAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Pand)
class PandAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Spoorbaandeel)
class SpoorbaandeelAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Terreindeel)
class TerreindeelAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Waterdeel)
class WaterdeelAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Wegdeel)
class WegdeelAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Wijk)
class WijkAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "wijk_code"]


@admin.register(Woonplaats)
class WoonplaatsAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(Overige)
class OverigeAdmin(admin.ModelAdmin):
    list_display = ["zaakobject"]


@admin.register(TerreinGebouwdObject)
class TerreinGebouwdObjectAdmin(admin.ModelAdmin):
    list_display = ["huishouden", "identificatie"]


@admin.register(WozDeelobject)
class WozDeelobjectAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "nummer_woz_deel_object"]


@admin.register(WozWaarde)
class WozWaardeAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "waardepeildatum"]


@admin.register(WozObject)
class WozObjectAdmin(admin.ModelAdmin):
    list_display = ["woz_deelobject", "woz_warde", "woz_object_nummer"]


@admin.register(ZakelijkRecht)
class ZakelijkRechtAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "identificatie"]


@admin.register(ZakelijkRechtHeeftAlsGerechtigde)
class ZakelijkRechtHeeftAlsGerechtigdeAdmin(admin.ModelAdmin):
    list_display = ["zakelijk_recht"]


@admin.register(KadastraleOnroerendeZaak)
class KadastraleOnroerendeZaakAdmin(admin.ModelAdmin):
    list_display = ["zaakobject", "zakelijk_recht", "kadastrale_identificatie"]
