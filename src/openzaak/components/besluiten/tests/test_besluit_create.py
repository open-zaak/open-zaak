# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.tests import JWTAuthMixin

from ..constants import VervalRedenen
from ..models import Besluit
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_besluittype_response, get_operation_url


class BesluitCreateTests(TypeCheckMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2018-09-06T12:08+0200")
    def test_us162_voeg_besluit_toe_aan_zaak(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        besluittype.zaaktypen.add(zaak.zaaktype)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        besluittype.informatieobjecttypen.add(io.informatieobjecttype)

        with self.subTest(part="besluit_create"):
            url = get_operation_url("besluit_create")

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",  # RSIN
                    "identificatie": "123123",
                    "besluittype": f"http://testserver{besluittype_url}",
                    "zaak": f"http://testserver{zaak_url}",
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
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
                    ("vervaldatum", str),
                    ("vervalreden", str),
                    ("publicatiedatum", type(None)),
                    ("verzenddatum", type(None)),
                    ("uiterlijke_reactiedatum", type(None)),
                ),
            )

            self.assertEqual(Besluit.objects.count(), 1)

            besluit = Besluit.objects.get()
            self.assertEqual(besluit.verantwoordelijke_organisatie, "517439943")
            self.assertEqual(besluit.besluittype, besluittype)
            self.assertEqual(besluit.zaak, zaak)
            self.assertEqual(besluit.datum, date(2018, 9, 6))
            self.assertEqual(besluit.toelichting, "Vergunning verleend.")
            self.assertEqual(besluit.ingangsdatum, date(2018, 10, 1))
            self.assertEqual(besluit.vervaldatum, date(2018, 11, 1))
            self.assertEqual(besluit.vervalreden, VervalRedenen.tijdelijk)

        with self.subTest(part="besluitinformatieobject_create"):
            url = get_operation_url("besluitinformatieobject_create")

            response = self.client.post(
                url,
                {
                    "besluit": reverse(besluit),
                    "informatieobject": f"http://testserver{io_url}",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assertResponseTypes(
                response.data, (("url", str), ("informatieobject", str))
            )

            self.assertEqual(besluit.besluitinformatieobject_set.count(), 1)
            self.assertEqual(
                besluit.besluitinformatieobject_set.get().informatieobject, io.canonical
            )

    def test_opvragen_informatieobjecten_besluit(self):
        besluit1, besluit2 = BesluitFactory.create_batch(2)

        besluit1_uri = reverse(besluit1)
        besluit2_uri = reverse(besluit2)

        BesluitInformatieObjectFactory.create_batch(3, besluit=besluit1)
        BesluitInformatieObjectFactory.create_batch(2, besluit=besluit2)

        base_uri = get_operation_url("besluitinformatieobject_list")

        response1 = self.client.get(
            base_uri,
            {"besluit": f"http://openzaak.nl{besluit1_uri}"},
            HTTP_HOST="openzaak.nl",
        )
        self.assertEqual(len(response1.data), 3)

        response2 = self.client.get(
            base_uri,
            {"besluit": f"http://openzaak.nl{besluit2_uri}"},
            HTTP_HOST="openzaak.nl",
        )
        self.assertEqual(len(response2.data), 2)

    def test_besluit_create_fail_besluittype_max_length(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)

        url = get_operation_url("besluit_create")

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": f"http://testserver/{'x'*1000}",
                "zaak": f"http://testserver{zaak_url}",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        max_length_errors = [
            e
            for e in response.data["invalid_params"]
            if e["name"] == "besluittype" and e["code"] == "max_length"
        ]
        self.assertEqual(len(max_length_errors), 1)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitCreateExternalURLsTests(TypeCheckMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create_external_besluittype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                "GET",
                besluittype,
                json=get_besluittype_response(catalogus, besluittype),
            )

            m.register_uri(
                "GET",
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

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",  # RSIN
                    "identificatie": "123123",
                    "besluittype": besluittype,
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_besluittype_fail_bad_url(self):
        url = reverse(Besluit)

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": "abcd",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_besluittype_fail_not_json_url(self):
        url = reverse(Besluit)

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": "http://example.com",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_besluittype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                "GET",
                besluittype,
                json={
                    "url": besluittype,
                    "catalogus": catalogus,
                    "zaaktypen": [],
                    "informatieobjecttypen": [],
                    "beginGeldigheid": "2018-01-01",
                    "eindeGeldigheid": None,
                    "concept": False,
                },
            )
            m.register_uri(
                "GET",
                catalogus,
                json={
                    "url": catalogus,
                    "domein": "PUB",
                    "informatieobjecttypen": [],
                    "zaaktypen": [],
                    "besluittypen": [besluittype],
                },
            )

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",  # RSIN
                    "identificatie": "123123",
                    "besluittype": besluittype,
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "invalid-resource")
