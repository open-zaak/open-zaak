# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import datetime

from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ..models import Gebruiksrechten
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenTests(JWTAuthMixin, APICMISTestCase):
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
                "informatieobject": f"http://testserver{eio_url}",
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
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

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
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

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
        for i in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = f"http://testserver{reverse(eio)}"
            GebruiksrechtenCMISFactory(informatieobject=eio_url)

        url = reverse(Gebruiksrechten)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_retrieve_multiple_gebruiksrechten(self):
        eio_1 = EnkelvoudigInformatieObjectFactory.create()
        eio_1_url = f"http://example.com{reverse(eio_1)}"

        eio_2 = EnkelvoudigInformatieObjectFactory.create()
        eio_2_url = f"http://example.com{reverse(eio_2)}"

        GebruiksrechtenCMISFactory(informatieobject=eio_1_url)
        GebruiksrechtenCMISFactory(informatieobject=eio_2_url)

        response = self.client.get(reverse("gebruiksrechten-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)
        self.assertTrue(
            eio_1_url == response.data[0]["informatieobject"]
            or eio_1_url == response.data[1]["informatieobject"]
        )
        self.assertTrue(
            eio_2_url == response.data[0]["informatieobject"]
            or eio_2_url == response.data[1]["informatieobject"]
        )

    def test_complete_edit(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(
            informatieobject=eio_url,
            omschrijving_voorwaarden="Test omschrijving voorwaarden",
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
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(
            informatieobject=eio_url,
            omschrijving_voorwaarden="Test omschrijving voorwaarden",
        )

        url = reverse(gebruiksrechten)

        gebruiksrechten_data = self.client.get(url).json()
        self.assertEqual(
            "Test omschrijving voorwaarden",
            gebruiksrechten_data["omschrijvingVoorwaarden"],
        )

        response = self.client.patch(
            url,
            {
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


@require_cmis
@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenFilterCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy("gebruiksrechten-list")

    def test_list_expand(self):
        response = self.client.get(self.url, {"expand": "informatieobject"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "CMIS not supported")
