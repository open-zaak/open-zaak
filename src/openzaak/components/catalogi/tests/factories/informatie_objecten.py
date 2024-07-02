# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

import factory
import factory.fuzzy

from ...models import InformatieObjectType
from .catalogus import CatalogusFactory
from .relatieklassen import ZaakTypeInformatieObjectTypeFactory


class InformatieObjectTypeFactory(factory.django.DjangoModelFactory):
    informatieobjectcategorie = factory.Faker("word")
    omschrijving = factory.Sequence(lambda n: "Informatie object type {}".format(n))
    catalogus = factory.SubFactory(CatalogusFactory)
    zaaktypen = factory.RelatedFactory(
        ZaakTypeInformatieObjectTypeFactory, "informatieobjecttype"
    )
    datum_begin_geldigheid = date(2018, 1, 1)
    omschrijving_generiek_informatieobjecttype = factory.Faker("word")
    omschrijving_generiek_definitie = factory.Faker("text")
    omschrijving_generiek_herkomst = factory.fuzzy.FuzzyText(length=12)
    omschrijving_generiek_hierarchie = factory.Faker("word")
    vertrouwelijkheidaanduiding = "openbaar"

    class Meta:
        model = InformatieObjectType

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )
