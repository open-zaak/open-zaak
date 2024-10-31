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

from openzaak.tests.utils import patch_resource_validator

from ..models import ZaakContactMoment
from .factories import ZaakContactMomentFactory, ZaakFactory

CONTACTMOMENTEN_BASE = "https://contactmomenten.nl/api/v1/"
CONTACTMOMENT = f"{CONTACTMOMENTEN_BASE}contactmomenten/1234"


def mock_contactmomenten_oas_get(m, base: str):
    mock_service_oas_get(m, url=base, service="contactmomenten")


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
@patch_resource_validator
class ZaakContactMomentTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_type=APITypes.orc,
            api_root=CONTACTMOMENTEN_BASE,
            label="contactmomenten",
            auth_type=AuthTypes.zgw,
        )

    def test_create(self, *mocks):
        zaak = ZaakFactory.create()
        url = reverse("zaakcontactmoment-list")

        with requests_mock.Mocker() as m:
            mock_contactmomenten_oas_get(m, CONTACTMOMENTEN_BASE)
            m.post(
                f"{CONTACTMOMENTEN_BASE}objectcontactmomenten",
                json={
                    "url": f"{CONTACTMOMENTEN_BASE}objectcontactmomenten/1",
                    "contactmoment": CONTACTMOMENT,
                    "object": f"http://testserver{reverse(zaak)}",
                    "objectType": "zaak",
                },
                status_code=201,
            )
            response = self.client.post(
                url, {"contactmoment": CONTACTMOMENT, "zaak": reverse(zaak)}
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaak_contactmoment = zaak.zaakcontactmoment_set.get()
        self.assertEqual(zaak_contactmoment.contactmoment, CONTACTMOMENT)
        self.assertEqual(
            zaak_contactmoment._objectcontactmoment,
            f"{CONTACTMOMENTEN_BASE}objectcontactmomenten/1",
        )

    def test_create_fail_sync(self, *mocks):
        zaak = ZaakFactory.create()
        url = reverse("zaakcontactmoment-list")

        with requests_mock.Mocker() as m:
            mock_contactmomenten_oas_get(m, CONTACTMOMENTEN_BASE)
            m.post(
                f"{CONTACTMOMENTEN_BASE}objectcontactmomenten",
                status_code=400,
            )
            response = self.client.post(
                url, {"contactmoment": CONTACTMOMENT, "zaak": reverse(zaak)}
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "contactmoment")
        self.assertEqual(error["code"], "pending-relations")

        self.assertEqual(ZaakContactMoment.objects.count(), 0)

    def test_delete(self, *mocks):
        zaak_contactmoment = ZaakContactMomentFactory.create(
            _objectcontactmoment=f"{CONTACTMOMENTEN_BASE}objectcontactmomenten/1"
        )
        zaak = zaak_contactmoment.zaak
        url = reverse(zaak_contactmoment)

        with requests_mock.Mocker() as m:
            mock_contactmomenten_oas_get(m, CONTACTMOMENTEN_BASE)
            m.delete(
                zaak_contactmoment._objectcontactmoment,
                status_code=204,
            )
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(zaak.zaakcontactmoment_set.exists())

    def test_delete_fail_sync(self, *mocks):
        zaak_contactmoment = ZaakContactMomentFactory.create(
            _objectcontactmoment=f"{CONTACTMOMENTEN_BASE}objectcontactmomenten/1"
        )
        url = reverse(zaak_contactmoment)

        with requests_mock.Mocker() as m:
            mock_contactmomenten_oas_get(m, CONTACTMOMENTEN_BASE)
            m.post(
                f"{CONTACTMOMENTEN_BASE}objectcontactmomenten",
                status_code=400,
            )
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "contactmoment")
        self.assertEqual(error["code"], "pending-relations")

        self.assertEqual(ZaakContactMoment.objects.count(), 1)


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    NOTIFICATIONS_DISABLED=True,
    ALLOWED_HOSTS=["testserver", "testserver.com"],
)
class ZaakContactMomentFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_zaak(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        ZaakContactMomentFactory.create(zaak=zaak)
        url = reverse("zaakcontactmoment-list")

        response = self.client.get(
            url,
            {"zaak": f"http://testserver.com{zaak_url}"},
            headers={"host": "testserver.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], f"http://testserver.com{zaak_url}")

    def test_filter_contactmoment(self):
        ZaakContactMomentFactory.create(contactmoment=CONTACTMOMENT)
        url = reverse("zaakcontactmoment-list")

        response = self.client.get(url, {"contactmoment": CONTACTMOMENT})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["contactmoment"], CONTACTMOMENT)
