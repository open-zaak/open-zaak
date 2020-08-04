# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import factory

from ...models import Catalogus


class CatalogusFactory(factory.django.DjangoModelFactory):
    _admin_name = factory.Sequence(lambda n: "Catalogus {}".format(n))
    domein = factory.Sequence(
        lambda n: chr((n % 26) + 65) * 5
    )  # AAAAA, BBBBB, etc. Repeat after ZZZZZ
    rsin = factory.Sequence(
        lambda n: "{}".format(n + 100000000)
    )  # charfield, that is 9 digit number
    contactpersoon_beheer_naam = factory.Sequence(
        lambda n: "Contact persoon beheer {}".format(n)
    )
    contactpersoon_beheer_telefoonnummer = "0612345678"
    contactpersoon_beheer_emailadres = factory.Sequence(
        lambda n: "contact_{}@example.com".format(n)
    )

    class Meta:
        model = Catalogus
