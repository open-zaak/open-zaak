# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, timedelta

import factory

from ...models import BesluitType
from .catalogus import CatalogusFactory
from .zaaktype import ZaakTypeFactory


class BesluitTypeFactory(factory.django.DjangoModelFactory):
    omschrijving = factory.Sequence(lambda n: "Besluittype {}".format(n))
    catalogus = factory.SubFactory(CatalogusFactory)
    reactietermijn = timedelta(days=14)
    publicatie_indicatie = False
    datum_begin_geldigheid = date(2018, 1, 1)

    class Meta:
        model = BesluitType

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )

    @factory.post_generation
    def informatieobjecttypen(self, create, extracted, **kwargs):
        # optional M2M, do nothing when no arguments are passed
        if not create:
            return

        if extracted:
            for informatieobjecttype in extracted:
                self.informatieobjecttypen.add(informatieobjecttype)

    @factory.post_generation
    def zaaktypen(self, create, extracted, **kwargs):
        # required M2M, if it is not passed in, create one
        if not extracted:
            extracted = [ZaakTypeFactory.create(catalogus=self.catalogus)]

        for zaak_type in extracted:
            self.zaaktypen.add(zaak_type)
