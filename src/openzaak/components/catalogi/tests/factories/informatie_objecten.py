from datetime import date

import factory

from ...models import InformatieObjectType
from .catalogus import CatalogusFactory
from .relatieklassen import ZaakInformatieobjectTypeFactory


class InformatieObjectTypeFactory(factory.django.DjangoModelFactory):
    omschrijving = factory.Sequence(lambda n: "Informatie object type {}".format(n))
    catalogus = factory.SubFactory(CatalogusFactory)
    zaaktypes = factory.RelatedFactory(
        ZaakInformatieobjectTypeFactory, "informatieobjecttype"
    )
    datum_begin_geldigheid = date(2018, 1, 1)

    class Meta:
        model = InformatieObjectType
