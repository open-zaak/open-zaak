# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _

from openzaak.utils.help_text import mark_experimental


class BetalingsIndicatie(models.TextChoices):
    nvt = "nvt", _("Er is geen sprake van te betalen, met de zaak gemoeide, kosten.")
    nog_niet = "nog_niet", _("De met de zaak gemoeide kosten zijn (nog) niet betaald.")
    gedeeltelijk = (
        "gedeeltelijk",
        _("De met de zaak gemoeide kosten zijn gedeeltelijk betaald."),
    )
    geheel = "geheel", _("De met de zaak gemoeide kosten zijn geheel betaald.")


class GeslachtsAanduiding(models.TextChoices):
    man = "m", _("Man")
    vrouw = "v", _("Vrouw")
    onbekend = "o", _("Onbekend")


class SoortRechtsvorm(models.TextChoices):
    besloten_vennootschap = "besloten_vennootschap", _("Besloten Vennootschap")
    cooperatie_europees_economische_samenwerking = (
        "cooperatie_europees_economische_samenwerking",
        _("Cooperatie, Europees Economische Samenwerking"),
    )
    europese_cooperatieve_vennootschap = (
        "europese_cooperatieve_venootschap",
        _("Europese Cooperatieve Venootschap"),
    )
    europese_naamloze_vennootschap = (
        "europese_naamloze_vennootschap",
        _("Europese Naamloze Vennootschap"),
    )
    kerkelijke_organisatie = "kerkelijke_organisatie", _("Kerkelijke Organisatie")
    naamloze_vennootschap = "naamloze_vennootschap", _("Naamloze Vennootschap")
    onderlinge_waarborg_maatschappij = (
        "onderlinge_waarborg_maatschappij",
        _("Onderlinge Waarborg Maatschappij"),
    )
    overig_privaatrechtelijke_rechtspersoon = (
        "overig_privaatrechtelijke_rechtspersoon",
        _("Overig privaatrechtelijke rechtspersoon"),
    )
    stichting = "stichting", _("Stichting")
    vereniging = "vereniging", _("Vereniging")
    vereniging_van_eigenaars = "vereniging_van_eigenaars", _("Vereniging van Eigenaars")
    publiekrechtelijke_rechtspersoon = (
        "publiekrechtelijke_rechtspersoon",
        _("Publiekrechtelijke Rechtspersoon"),
    )
    vennootschap_onder_firma = "vennootschap_onder_firma", _("Vennootschap onder Firma")
    maatschap = "maatschap", _("Maatschap")
    rederij = "rederij", _("Rederij")
    commanditaire_vennootschap = (
        "commanditaire_vennootschap",
        _("Commanditaire vennootschap"),
    )
    kapitaalvennootschap_binnen_eer = (
        "kapitaalvennootschap_binnen_eer",
        _("Kapitaalvennootschap binnen EER"),
    )
    overige_buitenlandse_rechtspersoon_vennootschap = (
        "overige_buitenlandse_rechtspersoon_vennootschap",
        _("Overige buitenlandse rechtspersoon vennootschap"),
    )
    kapitaalvennootschap_buiten_eer = (
        "kapitaalvennootschap_buiten_eer",
        _("Kapitaalvennootschap buiten EER"),
    )


class AardZaakRelatie(models.TextChoices):
    vervolg = (
        "vervolg",
        _("De andere zaak gaf aanleiding tot het starten van de onderhanden zaak."),
    )
    onderwerp = (
        "onderwerp",
        _("De andere zaak is relevant voor cq. is onderwerp van de onderhanden zaak."),
    )
    bijdrage = (
        "bijdrage",
        _(
            "Aan het bereiken van de uitkomst van de andere zaak levert de onderhanden zaak een bijdrage."
        ),
    )
    overig = ("overig", mark_experimental(_("Overig")))


# for zaaokbject models
class TyperingInrichtingselement(models.TextChoices):
    bak = "bak", _("Bak")
    bord = "bord", _("Bord")
    installatie = "installatie", _("Installatie")
    kast = "kast", _("Kast")
    mast = "mast", _("Mast")
    paal = "paal", _("Paal")
    sensor = "sensor", _("Sensor")
    straatmeubilair = "straatmeubilair", _("Straatmeubilair")
    waterinrichtingselement = "waterinrichtingselement", _("Waterinrichtingselement")
    weginrichtingselement = "weginrichtingselement", _("Weginrichtingselement")


class TyperingKunstwerk(models.TextChoices):
    keermuur = "keermuur", _("Keermuur")
    overkluizing = "overkluizing", _("Overkluizing")
    duiker = "duiker", _("Duiker")
    faunavoorziening = "faunavoorziening", _("Faunavoorziening")
    vispassage = "vispassage", _("Vispassage")
    bodemval = "bodemval", _("Bodemval")
    coupure = "coupure", _("Coupure")
    ponton = "ponton", _("Ponton")
    voorde = "voorde", _("Voorde")
    hoogspanningsmast = "hoogspanningsmast", _("Hoogspanningsmast")
    gemaal = "gemaal", _("Gemaal")
    perron = "perron", _("Perron")
    sluis = "sluis", _("Sluis")
    strekdam = "strekdam", _("Strekdam")
    steiger = "steiger", _("Steiger")
    stuw = "stuw", _("Stuw")


class TyperingWater(models.TextChoices):
    zee = "zee", _("Zee")
    waterloop = "waterloop", _("Waterloop")
    watervlakte = "watervlakte", _("Watervlakte")
    greppel_droge_sloot = "greppel_droge_sloot", _("Greppel, droge sloot")


# openzaak.components.zaken.constants.TypeSpoorbaan
class TypeSpoorbaan(models.TextChoices):
    breedspoor = "breedspoor", _("Breedspoor")
    normaalspoor = "normaalspoor", _("Normaalspoor")
    smalspoor = "smalspoor", _("Smalspoor")
    spoorbaan = "spoorbaan", _("Spoorbaan")


class IndicatieMachtiging(models.TextChoices):
    gemachtigde = (
        "gemachtigde",
        _(
            "De betrokkene in de rol bij de zaak is door een andere betrokkene bij "
            "dezelfde zaak gemachtigd om namens hem of haar te handelen"
        ),
    )
    machtiginggever = (
        "machtiginggever",
        _(
            "De betrokkene in de rol bij de zaak heeft een andere betrokkene bij "
            "dezelfde zaak gemachtigd om namens hem of haar te handelen"
        ),
    )
