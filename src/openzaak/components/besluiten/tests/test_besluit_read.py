# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.tests.utils import JWTAuthMixin

from .factories import BesluitFactory


class BesluitReadTests(TypeCheckMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_besluit_zaak_null_regression(self):
        """
        Assert that a besluit without zaak returns an empty string in the API.

        Uncovered in the tests with remote DRC integration, which performs validation
        of the Besluit resource. Open Zaak should not return `null`, but an empty
        string instead.
        """
        besluit = BesluitFactory.create(zaak=None)

        response = self.client.get(reverse(besluit))

        self.assertResponseTypes(
            response.data,
            (
                ("url", str),
                ("identificatie", str),
                ("verantwoordelijke_organisatie", str),
                ("besluittype", str),
                ("zaak", str),
                ("datum", str),
                ("toelichting", str),
                ("bestuursorgaan", str),
                ("ingangsdatum", str),
                ("vervaldatum", type(None)),
                ("vervalreden", str),
                ("publicatiedatum", type(None)),
                ("verzenddatum", type(None)),
                ("uiterlijke_reactiedatum", type(None)),
            ),
        )
