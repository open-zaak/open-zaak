# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory.fuzzy
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding


class ApplicatieFactory(factory.django.DjangoModelFactory):
    client_ids = factory.List(factory.Faker("word") for i in range(2))
    label = factory.Faker("word")

    class Meta:
        model = "authorizations.Applicatie"


class AutorisatieFactory(factory.django.DjangoModelFactory):
    applicatie = factory.SubFactory(ApplicatieFactory)
    component = factory.fuzzy.FuzzyChoice(ComponentTypes.values)
    zaaktype = factory.Faker("url")
    scopes = factory.List(factory.Faker("word") for i in range(3))
    max_vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(
        choices=VertrouwelijkheidsAanduiding.values
    )

    class Meta:
        model = "authorizations.Autorisatie"


class AutorisatieSpecFactory(factory.django.DjangoModelFactory):
    applicatie = factory.SubFactory(ApplicatieFactory)
    component = factory.fuzzy.FuzzyChoice(ComponentTypes.values)
    scopes = factory.List(factory.Faker("word") for i in range(3))
    max_vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(
        choices=VertrouwelijkheidsAanduiding.values
    )

    class Meta:
        model = "autorisaties.AutorisatieSpec"
