# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test.utils import override_settings

import requests_mock
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.tests.utils import JWTAuthMixin

from ..models import Besluit
from .factories import BesluitFactory
from .utils import get_besluittype_response, get_operation_url


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

    @override_settings(ALLOWED_HOSTS=["testserver"])
    @requests_mock.Mocker()
    def test_besluit_external_besluittype(self, m):
        catalogi_api = "https://externe.catalogus.nl/api/v1/"
        catalogus = f"{catalogi_api}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = f"{catalogi_api}besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        # setup mocks
        m.get(
            besluittype, json=get_besluittype_response(catalogus, besluittype),
        )
        m.get(
            catalogus,
            json={
                "url": catalogus,
                "domein": "PUB",
                "contactpersoonBeheerTelefoonnummer": "0612345678",
                "rsin": "517439943",
                "contactpersoonBeheerNaam": "Jan met de Pet",
                "contactpersoonBeheerEmailadres": "jan@petten.nl",
                "informatieobjecttypen": [],
                "zaaktypen": [],
                "besluittypen": [besluittype],
            },
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalogi_api)

        besluit = Besluit.objects.create(
            verantwoordelijke_organisatie="853162402",
            identificatie="ext",
            besluittype=besluittype,
            datum="2022-01-01",
            ingangsdatum="2022-01-01",
        )

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
