# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import factory
import factory.fuzzy
from vng_api_common.constants import ComponentTypes


class InternalServiceFactory(factory.django.DjangoModelFactory):
    api_type = factory.fuzzy.FuzzyChoice(ComponentTypes.values)

    class Meta:
        model = "config.InternalService"
        django_get_or_create = ("api_type",)
