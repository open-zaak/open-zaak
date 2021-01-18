# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

import factory

from ...models import InformatieObjectType
from .catalogus import CatalogusFactory
from .relatieklassen import ZaakTypeInformatieObjectTypeFactory


class InformatieObjectTypeFactory(factory.django.DjangoModelFactory):
    omschrijving = factory.Sequence(lambda n: "Informatie object type {}".format(n))
    catalogus = factory.SubFactory(CatalogusFactory)
    zaaktypen = factory.RelatedFactory(
        ZaakTypeInformatieObjectTypeFactory, "informatieobjecttype"
    )
    datum_begin_geldigheid = date(2018, 1, 1)

    class Meta:
        model = InformatieObjectType
