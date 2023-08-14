# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import timedelta

import factory

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
)
from openzaak.tests.utils import FkOrServiceUrlFactoryMixin


class BesluitFactory(FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory):
    verantwoordelijke_organisatie = factory.Faker("ssn", locale="nl_NL")
    besluittype = factory.SubFactory(BesluitTypeFactory)
    datum = factory.Faker("date_this_decade")

    class Meta:
        model = "besluiten.Besluit"

    class Params:
        for_zaak = factory.Trait(
            zaak=factory.SubFactory(
                "openzaak.components.zaken.tests.factories.ZaakFactory"
            )
        )
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )

    @factory.lazy_attribute
    def ingangsdatum(self):
        _ingangsdatum = factory.Faker(
            "date_between",
            start_date=self.datum,
            end_date=self.datum + timedelta(days=180),
        )
        return _ingangsdatum.evaluate(
            self, None, {"locale": _ingangsdatum._defaults["locale"]}
        )


class BesluitInformatieObjectFactory(
    FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory
):
    besluit = factory.SubFactory(BesluitFactory)
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)

    class Meta:
        model = "besluiten.BesluitInformatieObject"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )
