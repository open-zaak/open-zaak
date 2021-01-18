# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory

from ...models import StatusType
from .zaaktype import ZaakTypeFactory


class StatusTypeFactory(factory.django.DjangoModelFactory):
    statustypevolgnummer = factory.sequence(lambda n: n + 1)
    zaaktype = factory.SubFactory(ZaakTypeFactory)

    class Meta:
        model = StatusType
