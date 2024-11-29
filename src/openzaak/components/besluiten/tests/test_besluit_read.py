# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test.utils import override_settings, tag

import requests_mock
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.zaken.tests.utils import get_zaak_response
from openzaak.tests.utils import JWTAuthMixin

from .factories import BesluitFactory
from .utils import get_besluittype_response


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

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    @requests_mock.Mocker()
    def test_besluit_external_besluittype(self, m):
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/",
            api_type=APITypes.ztc,
        )
        catalogi_api = "https://externe.catalogus.nl/api/v1/"
        catalogus = f"{catalogi_api}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = f"{catalogi_api}besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        # setup mocks
        m.get(
            besluittype,
            json=get_besluittype_response(catalogus, besluittype),
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
        besluit = BesluitFactory.create(
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

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    @requests_mock.Mocker()
    def test_besluit_external_zaak(self, m):
        ServiceFactory.create(
            api_root="https://externe.zaken.nl/api/v1/",
            api_type=APITypes.zrc,
        )
        besluittype = BesluitTypeFactory.create(concept=False, zaaktypen=[])
        zaaktype = besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaken_api = "https://externe.zaken.nl/api/v1/"
        zaak = f"{zaken_api}zaken/b71f72ef-198d-44d8-af64-ae1932df830a"
        # setup mocks
        m.get(
            zaak,
            json=get_zaak_response(zaak, zaaktype_url),
        )
        besluit = BesluitFactory.create(
            verantwoordelijke_organisatie="853162402",
            identificatie="ext",
            besluittype=besluittype,
            datum="2022-01-01",
            ingangsdatum="2022-01-01",
            zaak=zaak,
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
