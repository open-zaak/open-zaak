# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class BetalingsIndicatie(DjangoChoices):
    nvt = ChoiceItem(
        "nvt", _("Er is geen sprake van te betalen, met de zaak gemoeide, kosten.")
    )
    nog_niet = ChoiceItem(
        "nog_niet", _("De met de zaak gemoeide kosten zijn (nog) niet betaald.")
    )
    gedeeltelijk = ChoiceItem(
        "gedeeltelijk", _("De met de zaak gemoeide kosten zijn gedeeltelijk betaald.")
    )
    geheel = ChoiceItem(
        "geheel", _("De met de zaak gemoeide kosten zijn geheel betaald.")
    )


class GeslachtsAanduiding(DjangoChoices):
    man = ChoiceItem("m", "Man")
    vrouw = ChoiceItem("v", "Vrouw")
    onbekend = ChoiceItem("o", "Onbekend")


class SoortRechtsvorm(DjangoChoices):
    besloten_vennootschap = ChoiceItem("besloten_vennootschap", "Besloten Vennootschap")
    cooperatie_europees_economische_samenwerking = ChoiceItem(
        "cooperatie_europees_economische_samenwerking",
        "Cooperatie, Europees Economische Samenwerking",
    )
    europese_cooperatieve_vennootschap = ChoiceItem(
        "europese_cooperatieve_venootschap", "Europese Cooperatieve Venootschap"
    )
    europese_naamloze_vennootschap = ChoiceItem(
        "europese_naamloze_vennootschap", "Europese Naamloze Vennootschap"
    )
    kerkelijke_organisatie = ChoiceItem(
        "kerkelijke_organisatie", "Kerkelijke Organisatie"
    )
    naamloze_vennootschap = ChoiceItem("naamloze_vennootschap", "Naamloze Vennootschap")
    onderlinge_waarborg_maatschappij = ChoiceItem(
        "onderlinge_waarborg_maatschappij", "Onderlinge Waarborg Maatschappij"
    )
    overig_privaatrechtelijke_rechtspersoon = ChoiceItem(
        "overig_privaatrechtelijke_rechtspersoon",
        "Overig privaatrechtelijke rechtspersoon",
    )
    stichting = ChoiceItem("stichting", "Stichting")
    vereniging = ChoiceItem("vereniging", "Vereniging")
    vereniging_van_eigenaars = ChoiceItem(
        "vereniging_van_eigenaars", "Vereniging van Eigenaars"
    )
    publiekrechtelijke_rechtspersoon = ChoiceItem(
        "publiekrechtelijke_rechtspersoon", "Publiekrechtelijke Rechtspersoon"
    )
    vennootschap_onder_firma = ChoiceItem(
        "vennootschap_onder_firma", "Vennootschap onder Firma"
    )
    maatschap = ChoiceItem("maatschap", "Maatschap")
    rederij = ChoiceItem("rederij", "Rederij")
    commanditaire_vennootschap = ChoiceItem(
        "commanditaire_vennootschap", "Commanditaire vennootschap"
    )
    kapitaalvennootschap_binnen_eer = ChoiceItem(
        "kapitaalvennootschap_binnen_eer", "Kapitaalvennootschap binnen EER"
    )
    overige_buitenlandse_rechtspersoon_vennootschap = ChoiceItem(
        "overige_buitenlandse_rechtspersoon_vennootschap",
        "Overige buitenlandse rechtspersoon vennootschap",
    )
    kapitaalvennootschap_buiten_eer = ChoiceItem(
        "kapitaalvennootschap_buiten_eer", "Kapitaalvennootschap buiten EER"
    )


class AardZaakRelatie(DjangoChoices):
    vervolg = ChoiceItem(
        "vervolg",
        _("De andere zaak gaf aanleiding tot het starten van de onderhanden zaak."),
    )
    onderwerp = ChoiceItem(
        "onderwerp",
        _("De andere zaak is relevant voor cq. is onderwerp van de onderhanden zaak."),
    )
    bijdrage = ChoiceItem(
        "bijdrage",
        _(
            "Aan het bereiken van de uitkomst van de andere zaak levert de onderhanden zaak een bijdrage."
        ),
    )


# for zaaokbject models
class TyperingInrichtingselement(DjangoChoices):
    bak = ChoiceItem("bak", "Bak")
    bord = ChoiceItem("bord", "Bord")
    installatie = ChoiceItem("installatie", "Installatie")
    kast = ChoiceItem("kast", "Kast")
    mast = ChoiceItem("mast", "Mast")
    paal = ChoiceItem("paal", "Paal")
    sensor = ChoiceItem("sensor", "Sensor")
    straatmeubilair = ChoiceItem("straatmeubilair", "Straatmeubilair")
    waterinrichtingselement = ChoiceItem(
        "waterinrichtingselement", "Waterinrichtingselement"
    )
    weginrichtingselement = ChoiceItem("weginrichtingselement", "Weginrichtingselement")


class TyperingKunstwerk(DjangoChoices):
    keermuur = ChoiceItem("keermuur", "Keermuur")
    overkluizing = ChoiceItem("overkluizing", "Overkluizing")
    duiker = ChoiceItem("duiker", "Duiker")
    faunavoorziening = ChoiceItem("faunavoorziening", "Faunavoorziening")
    vispassage = ChoiceItem("vispassage", "Vispassage")
    bodemval = ChoiceItem("bodemval", "Bodemval")
    coupure = ChoiceItem("coupure", "Coupure")
    ponton = ChoiceItem("ponton", "Ponton")
    voorde = ChoiceItem("voorde", "Voorde")
    hoogspanningsmast = ChoiceItem("hoogspanningsmast", "Hoogspanningsmast")
    gemaal = ChoiceItem("gemaal", "Gemaal")
    perron = ChoiceItem("perron", "Perron")
    sluis = ChoiceItem("sluis", "Sluis")
    strekdam = ChoiceItem("strekdam", "Strekdam")
    steiger = ChoiceItem("steiger", "Steiger")
    stuw = ChoiceItem("stuw", "Stuw")


class TyperingWater(DjangoChoices):
    zee = ChoiceItem("zee", "Zee")
    waterloop = ChoiceItem("waterloop", "Waterloop")
    watervlakte = ChoiceItem("watervlakte", "Watervlakte")
    greppel_droge_sloot = ChoiceItem("greppel_droge_sloot", "Greppel, droge sloot")


class TypeSpoorbaan(DjangoChoices):
    breedspoor = ChoiceItem("breedspoor")
    normaalspoor = ChoiceItem("normaalspoor")
    smalspoor = ChoiceItem("smalspoor")
    spoorbaan = ChoiceItem("spoorbaan")


class IndicatieMachtiging(DjangoChoices):
    gemachtigde = ChoiceItem(
        "gemachtigde",
        _(
            "De betrokkene in de rol bij de zaak is door een andere betrokkene bij "
            "dezelfde zaak gemachtigd om namens hem of haar te handelen"
        ),
    )
    machtiginggever = ChoiceItem(
        "machtiginggever",
        _(
            "De betrokkene in de rol bij de zaak heeft een andere betrokkene "
            "bij dezelfde zaak gemachtigd om namens hem of haar te handelen"
        ),
    )
