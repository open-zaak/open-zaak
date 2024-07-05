# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import datetime

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from ..models import Gebruiksrechten
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory


class GebruiksrechtenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create(self):
        url = reverse("gebruiksrechten-list")
        eio = EnkelvoudigInformatieObjectFactory.create(
            creatiedatum=datetime.date(2018, 12, 24)
        )
        eio_url = reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"uuid": eio.uuid},
        )

        eio_detail = self.client.get(eio_url)

        self.assertIsNone(eio_detail.json()["indicatieGebruiksrecht"])

        response = self.client.post(
            url,
            {
                "informatieobject": eio_url,
                "startdatum": "2018-12-24T00:00:00Z",
                "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # ensure that the indication is updated now
        eio_detail = self.client.get(eio_url)
        self.assertTrue(eio_detail.json()["indicatieGebruiksrecht"])

    def test_block_clearing_indication(self):
        """
        If gebruiksrechten exist, you cannot change the indicatieGebruiksrechten
        anymore.
        """
        gebruiksrechten = GebruiksrechtenFactory.create()

        url = reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"uuid": gebruiksrechten.get_informatieobject().uuid},
        )

        for invalid_value in (None, False):
            data = {"indicatieGebruiksrecht": invalid_value}
            response = self.client.patch(url, data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "indicatieGebruiksrecht")
            self.assertEqual(error["code"], "existing-gebruiksrechten")

    def test_block_setting_indication_true(self):
        """
        Assert that it's not possible to set the indication to true if there are
        no gebruiksrechten.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid})

        response = self.client.patch(url, {"indicatieGebruiksrecht": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "indicatieGebruiksrecht")
        self.assertEqual(error["code"], "missing-gebruiksrechten")

    def test_delete_gebruiksrechten(self):
        gebruiksrechten = GebruiksrechtenFactory.create()

        url = reverse(gebruiksrechten)
        eio_url = reverse(gebruiksrechten.get_informatieobject())

        eio_data = self.client.get(eio_url).json()
        self.assertTrue(eio_data["indicatieGebruiksrecht"])

        # delete the gebruiksrechten
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        eio_data = self.client.get(eio_url).json()
        self.assertIsNone(eio_data["indicatieGebruiksrecht"])

    def test_validate_unknown_query_params(self):
        GebruiksrechtenFactory.create_batch(2)

        url = reverse(Gebruiksrechten)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_complete_edit(self):
        gebruiksrechten = GebruiksrechtenFactory.create(
            omschrijving_voorwaarden="Test omschrijving voorwaarden"
        )

        url = reverse(gebruiksrechten)

        gebruiksrechten_data = self.client.get(url).json()
        self.assertEqual(
            "Test omschrijving voorwaarden",
            gebruiksrechten_data["omschrijvingVoorwaarden"],
        )

        response = self.client.put(
            url,
            {
                "informatieobject": reverse(gebruiksrechten.get_informatieobject()),
                "startdatum": "2018-12-24T00:00:00Z",
                "omschrijvingVoorwaarden": "Aangepaste omschrijving voorwaarden",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            "Aangepaste omschrijving voorwaarden",
            response.data["omschrijving_voorwaarden"],
        )

        updated_gebruiksrechten_data = self.client.get(url).json()
        self.assertEqual(
            "Aangepaste omschrijving voorwaarden",
            updated_gebruiksrechten_data["omschrijvingVoorwaarden"],
        )

    def test_partial_edit(self):
        gebruiksrechten = GebruiksrechtenFactory.create(
            omschrijving_voorwaarden="Test omschrijving voorwaarden"
        )

        url = reverse(gebruiksrechten)

        gebruiksrechten_data = self.client.get(url).json()
        self.assertEqual(
            "Test omschrijving voorwaarden",
            gebruiksrechten_data["omschrijvingVoorwaarden"],
        )

        response = self.client.put(
            url,
            {
                "informatieobject": reverse(gebruiksrechten.get_informatieobject()),
                "startdatum": "2018-12-24T00:00:00Z",
                "omschrijvingVoorwaarden": "Aangepaste omschrijving voorwaarden",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            "Aangepaste omschrijving voorwaarden",
            response.data["omschrijving_voorwaarden"],
        )

        updated_gebruiksrechten_data = self.client.get(url).json()
        self.assertEqual(
            "Aangepaste omschrijving voorwaarden",
            updated_gebruiksrechten_data["omschrijvingVoorwaarden"],
        )


class GebruiksrechtenFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy("gebruiksrechten-list")

    def test_list_expand(self):
        gebruiksrechten = GebruiksrechtenFactory.create()

        gebruiksrechten_data = self.client.get(reverse(gebruiksrechten)).json()
        io_data = self.client.get(
            reverse(gebruiksrechten.get_informatieobject())
        ).json()
        iotype_data = self.client.get(
            reverse(gebruiksrechten.get_informatieobject().informatieobjecttype)
        ).json()

        response = self.client.get(
            self.url,
            {"expand": "informatieobject,informatieobject.informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_results = [
            {
                **gebruiksrechten_data,
                "_expand": {
                    "informatieobject": {
                        **io_data,
                        "_expand": {"informatieobjecttype": iotype_data},
                    }
                },
            }
        ]
        self.assertEqual(data, expected_results)

    def test_retreive_expand(self):
        gebruiksrechten = GebruiksrechtenFactory.create()
        url = reverse(gebruiksrechten)

        gebruiksrechten_data = self.client.get(url).json()
        io_data = self.client.get(
            reverse(gebruiksrechten.get_informatieobject())
        ).json()
        iotype_data = self.client.get(
            reverse(gebruiksrechten.get_informatieobject().informatieobjecttype)
        ).json()

        response = self.client.get(
            url,
            {"expand": "informatieobject,informatieobject.informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_results = {
            **gebruiksrechten_data,
            "_expand": {
                "informatieobject": {
                    **io_data,
                    "_expand": {"informatieobjecttype": iotype_data},
                }
            },
        }
        self.assertEqual(data, expected_results)
