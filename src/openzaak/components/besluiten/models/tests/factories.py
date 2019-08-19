from datetime import timedelta

from django.utils import timezone

import factory
from openzaak.components.catalogi.models.tests.factories import (
    BesluitTypeFactory
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory
)


class BesluitFactory(factory.django.DjangoModelFactory):
    verantwoordelijke_organisatie = factory.Faker('ssn', locale='nl_NL')
    besluittype = factory.SubFactory(BesluitTypeFactory)
    datum = factory.Faker('date_this_decade')

    class Meta:
        model = 'besluiten.Besluit'

    class Params:
        for_zaak = factory.Trait(
            zaak=factory.SubFactory(
                "openzaak.components.zaken.models.tests.factories.ZaakFactory"
            ),
        )

    @factory.lazy_attribute
    def ingangsdatum(self):
        _ingangsdatum = factory.Faker(
            'date_time_between',
            start_date=self.datum,
            end_date=self.datum + timedelta(days=180),
            tzinfo=timezone.utc
        )
        return _ingangsdatum.evaluate(self, None, None)


class BesluitInformatieObjectFactory(factory.django.DjangoModelFactory):
    besluit = factory.SubFactory(BesluitFactory)
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)

    class Meta:
        model = 'besluiten.BesluitInformatieObject'
