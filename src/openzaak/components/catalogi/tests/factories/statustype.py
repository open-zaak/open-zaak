# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory

from ...models import CheckListItem, StatusType
from .zaaktype import ZaakTypeFactory


class StatusTypeFactory(factory.django.DjangoModelFactory):
    statustypevolgnummer = factory.sequence(lambda n: n + 1)
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    statustype_omschrijving = factory.Faker("sentence", locale="nl")

    class Meta:
        model = StatusType

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


class CheckListItemFactory(factory.django.DjangoModelFactory):
    statustype = factory.SubFactory(StatusTypeFactory)
    itemnaam = factory.Sequence(lambda n: "Item {}".format(n))
    vraagstelling = factory.Faker("sentence")

    class Meta:
        model = CheckListItem
