# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_validation_errors, reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test import mock_service_oas_get
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.models import ZaakVerzoek
from openzaak.components.zaken.tests.factories import ZaakFactory, ZaakVerzoekFactory
from openzaak.tests.utils import patch_resource_validator

VERZOEKEN_BASE = "https://verzoeken.nl/api/v1/"
VERZOEK = f"{VERZOEKEN_BASE}verzoeken/1234"


def mock_verzoeken_oas_get(m, base):
    mock_service_oas_get(m, url=base, service="verzoeken")


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
@patch_resource_validator
class ZaakVerzoekTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_type=APITypes.orc,
            api_root=VERZOEKEN_BASE,
            label="verzoeken",
            auth_type=AuthTypes.zgw,
        )

    def test_create(self, *m):
        zaak = ZaakFactory.create()
        url = reverse("zaakverzoek-list")

        with requests_mock.Mocker() as m:
            mock_verzoeken_oas_get(m, VERZOEKEN_BASE)
            m.post(
                f"{VERZOEKEN_BASE}objectverzoeken",
                json={
                    "url": f"{VERZOEKEN_BASE}objectverzoeken/1",
                    "verzoek": VERZOEK,
                    "object": f"http://testserver{reverse(zaak)}",
                    "objectType": "zaak",
                },
                status_code=201,
            )
            response = self.client.post(
                url, {"verzoek": VERZOEK, "zaak": reverse(zaak)}
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaak_verzoek = zaak.zaakverzoek_set.get()
        self.assertEqual(zaak_verzoek.verzoek, VERZOEK)
        self.assertEqual(
            zaak_verzoek._objectverzoek,
            f"{VERZOEKEN_BASE}objectverzoeken/1",
        )

    def test_create_fail_sync(self, *m):
        zaak = ZaakFactory.create()
        url = reverse("zaakverzoek-list")

        with requests_mock.Mocker() as m:
            mock_verzoeken_oas_get(m, VERZOEKEN_BASE)
            m.post(
                f"{VERZOEKEN_BASE}objectverzoeken",
                status_code=400,
            )
            response = self.client.post(
                url, {"verzoek": VERZOEK, "zaak": reverse(zaak)}
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "verzoek")
        self.assertEqual(error["code"], "pending-relations")

        self.assertEqual(ZaakVerzoek.objects.count(), 0)

    def test_delete(self, *m):
        zaak_verzoek = ZaakVerzoekFactory.create(
            _objectverzoek=f"{VERZOEKEN_BASE}objectverzoeken/1"
        )
        zaak = zaak_verzoek.zaak
        url = reverse(zaak_verzoek)

        with requests_mock.Mocker() as m:
            mock_verzoeken_oas_get(m, VERZOEKEN_BASE)
            m.delete(
                zaak_verzoek._objectverzoek,
                status_code=204,
            )
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(zaak.zaakverzoek_set.exists())

    def test_detele_fail_sync(self, *m):
        zaak_verzoek = ZaakVerzoekFactory.create(
            _objectverzoek=f"{VERZOEKEN_BASE}objectverzoeken/1"
        )
        url = reverse(zaak_verzoek)

        with requests_mock.Mocker() as m:
            mock_verzoeken_oas_get(m, VERZOEKEN_BASE)
            m.delete(
                f"{VERZOEKEN_BASE}objectverzoeken",
                status_code=400,
            )
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "verzoek")
        self.assertEqual(error["code"], "pending-relations")

        self.assertEqual(ZaakVerzoek.objects.count(), 1)


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakVerzoekFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_filter_zaak(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        ZaakVerzoekFactory.create(zaak=zaak)
        list_url = reverse(ZaakVerzoek)

        response = self.client.get(
            list_url,
            {"zaak": f"http://testserver.com{zaak_url}"},
            headers={"host": "testserver.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver.com{zaak_url}")

    def test_filter_verzoek(self):
        ZaakVerzoekFactory.create(verzoek=VERZOEK)
        list_url = reverse(ZaakVerzoek)

        response = self.client.get(list_url, {"verzoek": VERZOEK})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["verzoek"], VERZOEK)
