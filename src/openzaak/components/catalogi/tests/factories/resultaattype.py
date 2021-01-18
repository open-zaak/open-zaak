# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory
import factory.fuzzy
from dateutil.relativedelta import relativedelta

from openzaak.utils.tests import no_fetch

from ...models import ResultaatType
from .zaaktype import ZaakTypeFactory


class ResultaatTypeFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    omschrijving = factory.Sequence(lambda n: f"resultaattype {n}")
    resultaattypeomschrijving = no_fetch
    omschrijving_generiek = factory.Faker("word")
    selectielijstklasse = factory.Faker("url")
    archiefnominatie = factory.fuzzy.FuzzyChoice(["blijvend_bewaren", "vernietigen"])
    archiefactietermijn = relativedelta(years=10)

    class Meta:
        model = ResultaatType
