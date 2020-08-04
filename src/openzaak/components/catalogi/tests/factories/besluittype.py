# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, timedelta

import factory

from ...models import BesluitType
from .catalogus import CatalogusFactory
from .zaaktype import ZaakTypeFactory


class BesluitTypeFactory(factory.django.DjangoModelFactory):
    omschrijving = "Besluittype"
    catalogus = factory.SubFactory(CatalogusFactory)
    reactietermijn = timedelta(days=14)
    publicatie_indicatie = False
    datum_begin_geldigheid = date(2018, 1, 1)

    class Meta:
        model = BesluitType

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

        dates_begin_geldigheid = []
        for zaak_type in extracted:
            dates_begin_geldigheid.append(zaak_type.datum_begin_geldigheid)
            self.zaaktypen.add(zaak_type)

        # sort the list on python datetime.date(), the first element of the tuple, and then
        # use the OnvolledigeDatum value (second element in tuple) as the value
        dates_begin_geldigheid.sort()
        self.datum_begin_geldigheid = dates_begin_geldigheid[0]
