# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin

from openzaak.utils.admin import EditInlineAdminMixin

from ..models import (
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    SubVerblijfBuitenland,
    Vestiging,
)
from .objecten import AdresInline


@admin.register(SubVerblijfBuitenland)
class SubVerblijfBuitenlandAdmin(admin.ModelAdmin):
    list_display = (
        "natuurlijkpersoon",
        "nietnatuurlijkpersoon",
        "vestiging",
        "lnd_landcode",
    )
    list_filter = ("lnd_landcode",)
    search_fields = ("lnd_landcode", "lnd_landnaam", "sub_adres_buitenland_1")
    ordering = ("lnd_landcode",)
    raw_id_fields = ("natuurlijkpersoon", "nietnatuurlijkpersoon", "vestiging")


class SubVerblijfBuitenlandInline(EditInlineAdminMixin, admin.TabularInline):
    model = SubVerblijfBuitenland
    fields = SubVerblijfBuitenlandAdmin.list_display


@admin.register(NatuurlijkPersoon)
class NatuurlijkPersoonAdmin(admin.ModelAdmin):
    list_display = (
        "rol",
        "zaakobject",
        "zakelijk_rechtHeeft_als_gerechtigde",
        "inp_bsn",
        "anp_identificatie",
        "inp_a_nummer",
    )
    search_fields = ("inp_bsn", "anp_identificatie", "rol__uuid", "zaakobject__uuid")
    ordering = ("inp_bsn", "anp_identificatie")
    raw_id_fields = ("rol", "zaakobject", "zakelijk_rechtHeeft_als_gerechtigde")
    inlines = [SubVerblijfBuitenlandInline, AdresInline]


@admin.register(NietNatuurlijkPersoon)
class NietNatuurlijkPersoonAdmin(admin.ModelAdmin):
    list_display = (
        "rol",
        "zaakobject",
        "zakelijk_rechtHeeft_als_gerechtigde",
        "inn_nnp_id",
        "ann_identificatie",
    )
    search_fields = (
        "inn_nnp_id",
        "ann_identificatie",
        "statutaire_naam",
        "rol__uuid",
        "zaakobject__uuid",
    )
    ordering = ("inn_nnp_id", "ann_identificatie")
    raw_id_fields = ("rol", "zaakobject", "zakelijk_rechtHeeft_als_gerechtigde")
    inlines = [SubVerblijfBuitenlandInline]


@admin.register(OrganisatorischeEenheid)
class OrganisatorischeEenheidAdmin(admin.ModelAdmin):
    list_display = ("rol", "zaakobject", "identificatie")
    search_fields = ("identificatie", "naam", "rol__uuid", "zaakobject__uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("rol", "zaakobject")


@admin.register(Vestiging)
class VestigingAdmin(admin.ModelAdmin):
    list_display = ("rol", "zaakobject", "vestigings_nummer")
    search_fields = (
        "vestigings_nummer",
        "handelsnaam",
        "rol__uuid",
        "zaakobject__uuid",
    )
    ordering = ("vestigings_nummer",)
    inlines = [SubVerblijfBuitenlandInline, AdresInline]
    raw_id_fields = ("rol", "zaakobject")


@admin.register(Medewerker)
class MedewerkerAdmin(admin.ModelAdmin):
    list_display = ("rol", "zaakobject", "identificatie")
    search_fields = ("identificatie", "achternaam", "rol__uuid", "zaakobject__uuid")
    ordering = ("identificatie",)
    raw_id_fields = ("rol", "zaakobject")


# inline admin classes
class NatuurlijkPersoonInline(EditInlineAdminMixin, admin.TabularInline):
    model = NatuurlijkPersoon
    fields = NatuurlijkPersoonAdmin.list_display


class NietNatuurlijkPersoonInline(EditInlineAdminMixin, admin.TabularInline):
    model = NietNatuurlijkPersoon
    fields = NietNatuurlijkPersoonAdmin.list_display


class OrganisatorischeEenheidInline(EditInlineAdminMixin, admin.TabularInline):
    model = OrganisatorischeEenheid
    fields = OrganisatorischeEenheidAdmin.list_display


class VestigingInline(EditInlineAdminMixin, admin.TabularInline):
    model = Vestiging
    fields = VestigingAdmin.list_display


class MedewerkerInline(EditInlineAdminMixin, admin.TabularInline):
    model = Medewerker
    fields = MedewerkerAdmin.list_display
