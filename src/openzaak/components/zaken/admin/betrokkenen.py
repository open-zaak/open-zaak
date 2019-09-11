from django.contrib import admin

from ..models import (
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    SubVerblijfBuitenland,
    Vestiging,
)


@admin.register(NatuurlijkPersoon)
class NatuurlijkPersoonAdmin(admin.ModelAdmin):
    list_display = [
        "rol",
        "zaakobject",
        "zakelijk_rechtHeeft_als_gerechtigde",
        "inp_bsn",
        "anp_identificatie",
        "inp_a_nummer",
    ]


@admin.register(NietNatuurlijkPersoon)
class NietNatuurlijkPersoonAdmin(admin.ModelAdmin):
    list_display = [
        "rol",
        "zaakobject",
        "zakelijk_rechtHeeft_als_gerechtigde",
        "inn_nnp_id",
        "ann_identificatie",
    ]


@admin.register(OrganisatorischeEenheid)
class OrganisatorischeEenheidAdmin(admin.ModelAdmin):
    list_display = ["rol", "zaakobject", "identificatie"]


@admin.register(Vestiging)
class VestigingAdmin(admin.ModelAdmin):
    list_display = ["rol", "zaakobject", "vestigings_nummer"]


@admin.register(Medewerker)
class MedewerkerAdmin(admin.ModelAdmin):
    list_display = ["rol", "zaakobject", "identificatie"]


@admin.register(SubVerblijfBuitenland)
class SubVerblijfBuitenlandAdmin(admin.ModelAdmin):
    list_display = [
        "natuurlijkpersoon",
        "nietnatuurlijkpersoon",
        "vestiging",
        "lnd_landcode",
    ]
