# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory.fuzzy
from vng_api_common.constants import (  # VA_MAPPING,
    ComponentTypes,
    VertrouwelijkheidsAanduiding,
)

from openzaak.components.catalogi.tests.factories import CatalogusFactory


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

    # @factory.post_generation
    # def set_max_vertrouwelijkheidaanduiding_int(obj, create, extracted, **kwargs):
    #     if not obj._max_vertrouwelijkheidaanduiding:  # If not explicitly provided
    #         obj._max_vertrouwelijkheidaanduiding = VA_MAPPING[
    #             obj.max_vertrouwelijkheidaanduiding.value
    #         ]

    class Meta:
        model = "authorizations.Autorisatie"


class CatalogusAutorisatieFactory(factory.django.DjangoModelFactory):
    applicatie = factory.SubFactory(ApplicatieFactory)
    component = factory.fuzzy.FuzzyChoice(ComponentTypes.values)
    scopes = factory.List(factory.Faker("word") for i in range(3))
    max_vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(
        choices=VertrouwelijkheidsAanduiding.values
    )
    catalogus = factory.SubFactory(CatalogusFactory)

    class Meta:
        model = "autorisaties.CatalogusAutorisatie"
