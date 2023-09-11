# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import factory

from ...models import ZaakObjectType
from .zaaktype import ZaakTypeFactory


class ZaakObjectTypeFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    ander_objecttype = factory.Faker("pybool")
    objecttype = factory.Faker("url")
    relatie_omschrijving = factory.Faker("word")

    class Meta:
        model = ZaakObjectType

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )
