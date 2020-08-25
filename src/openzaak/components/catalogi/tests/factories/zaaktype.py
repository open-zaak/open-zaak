# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, timedelta

import factory
import factory.fuzzy

from ...constants import InternExtern
from ...models import ZaakType
from .catalogus import CatalogusFactory
from .relatieklassen import ZaakTypenRelatieFactory  # noqa

ZAAKTYPEN = [
    "Melding behandelen",
    "Toetsing uitvoeren",
    "Vergunningaanvraag regulier behandelen",
    "Vergunningaanvraag uitgebreid behandelen",
    "Vooroverleg voeren",
    "Zienswijze behandelen",
    "Bestuursdwang ten uitvoer leggen",
    "Handhavingsbesluit nemen",
    "Handhavingsverzoek behandelen",
    "Last onder dwangsom ten uitvoer leggen",
    "Toezicht uitvoeren",
    "Advies verstrekken",
    "Beroep behandelen",
    "Bezwaar behandelen",
    "Incidentmelding behandelen",
    "Voorlopige voorziening behandelen",
]


class ZaakTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_omschrijving = factory.Faker("bs")
    doel = factory.Faker("paragraph")
    aanleiding = factory.Faker("paragraph")
    indicatie_intern_of_extern = factory.fuzzy.FuzzyChoice(choices=InternExtern.values)
    handeling_initiator = factory.fuzzy.FuzzyChoice(["aanvragen", "indienen", "melden"])
    onderwerp = factory.fuzzy.FuzzyChoice(["Evenementvergunning", "Geboorte", "Klacht"])
    handeling_behandelaar = factory.fuzzy.FuzzyChoice(
        ["behandelen", "uitvoeren", "vaststellen", "onderhouden"]
    )
    doorlooptijd_behandeling = timedelta(days=30)
    opschorting_en_aanhouding_mogelijk = factory.Faker("pybool")
    verlenging_mogelijk = factory.Faker("pybool")
    publicatie_indicatie = factory.Faker("pybool")
    catalogus = factory.SubFactory(CatalogusFactory)
    referentieproces_naam = factory.Sequence(lambda n: "ReferentieProces {}".format(n))
    producten_of_diensten = ["https://example.com/product/123"]

    datum_begin_geldigheid = date(2018, 1, 1)
    versiedatum = date(2018, 1, 1)
    selectielijst_procestype_jaar = 2017

    # this one is optional, if its added as below, it will keep adding related
    # ZaakTypes (and reach max recursion depth)
    # heeft_gerelateerd = factory.RelatedFactory(ZaakTypenRelatieFactory, 'zaaktype_van')

    class Meta:
        model = ZaakType

    @factory.lazy_attribute
    def verlengingstermijn(obj):
        if not obj.verlenging_mogelijk:
            return None
        return timedelta(days=30)
