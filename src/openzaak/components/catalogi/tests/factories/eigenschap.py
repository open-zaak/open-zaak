# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory

from ...constants import FormaatChoices
from ...models import Eigenschap, EigenschapSpecificatie
from .zaaktype import ZaakTypeFactory


class EigenschapSpecificatieFactory(factory.django.DjangoModelFactory):
    groep = "groep"
    formaat = FormaatChoices.tekst
    lengte = "20"
    kardinaliteit = "1"
    waardenverzameling = []  # ArrayField has blank=True but not null=True

    class Meta:
        model = EigenschapSpecificatie


class EigenschapFactory(factory.django.DjangoModelFactory):
    eigenschapnaam = factory.Sequence(lambda n: "eigenschap {}".format(n))
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    specificatie_van_eigenschap = factory.SubFactory(EigenschapSpecificatieFactory)

    class Meta:
        model = Eigenschap

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )
