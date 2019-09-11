from datetime import date, timedelta

import factory
import factory.fuzzy

from ...constants import InternExtern
from ...models import BronCatalogus, BronZaakType, Formulier, ZaakObjectType, ZaakType
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


class FormulierFactory(factory.django.DjangoModelFactory):
    naam = factory.Sequence(lambda n: "Formulier {}".format(n))

    class Meta:
        model = Formulier


class BronCatalogusFactory(factory.django.DjangoModelFactory):
    domein = factory.Sequence(
        lambda n: chr((n % 26) + 65) * 5
    )  # AAAAA, BBBBB, etc. Repeat after ZZZZZ
    rsin = factory.Sequence(
        lambda n: "{}".format(n + 100000000)
    )  # charfield, that is 9 digit number

    class Meta:
        model = BronCatalogus


class BronZaakTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.Sequence(lambda n: n)

    class Meta:
        model = BronZaakType


class ZaakTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.Sequence(lambda n: n)
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

    # this one is optional, if its added as below, it will keep adding related ZaakTypes (and reach max recursion depth)
    # heeft_gerelateerd = factory.RelatedFactory(ZaakTypenRelatieFactory, 'zaaktype_van')

    class Meta:
        model = ZaakType

    @factory.lazy_attribute
    def verlengingstermijn(obj):
        if not obj.verlenging_mogelijk:
            return None
        return timedelta(days=30)

    @factory.post_generation
    def is_deelzaaktype_van(self, create, extracted, **kwargs):
        # optional M2M, do nothing when no arguments are passed
        if not create:
            return

        if extracted:
            for zaaktype in extracted:
                self.is_deelzaaktype_van.add(zaaktype)


class ZaakObjectTypeFactory(factory.django.DjangoModelFactory):
    is_relevant_voor = factory.SubFactory(ZaakTypeFactory)
    datum_begin_geldigheid = factory.SelfAttribute(
        "is_relevant_voor.datum_begin_geldigheid"
    )

    class Meta:
        model = ZaakObjectType
