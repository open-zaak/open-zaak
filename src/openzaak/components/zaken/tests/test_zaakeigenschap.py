# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als behandelaar wil ik locatie- en/of objectinformatie bij de melding
ontvangen, zodat ik voldoende details weet om de melding op te volgen.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/52
"""
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import EigenschapFactory
from openzaak.utils.tests import JWTAuthMixin

from ..models import ZaakEigenschap
from .factories import ZaakEigenschapFactory, ZaakFactory
from .utils import get_eigenschap_response, get_operation_url, get_zaaktype_response


class US52TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zet_eigenschappen(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(
            eigenschapnaam="foobar", zaaktype=zaak.zaaktype
        )
        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": zaak_url,
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "overlast_water",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakeigenschap = ZaakEigenschap.objects.get()
        self.assertEqual(zaakeigenschap.zaak, zaak)
        detail_url = get_operation_url(
            "zaakeigenschap_read", zaak_uuid=zaak.uuid, uuid=zaakeigenschap.uuid
        )
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(zaakeigenschap.uuid),
                "naam": "foobar",
                "zaak": f"http://testserver{zaak_url}",
                "eigenschap": f"http://testserver{eigenschap_url}",
                "waarde": "overlast_water",
            },
        )

    def test_lees_eigenschappen(self):
        zaak = ZaakFactory.create()
        ZaakEigenschapFactory.create_batch(3, zaak=zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(len(response_data), 3)
        for obj in response_data:
            with self.subTest(obj=obj):
                self.assertResponseTypes(
                    obj,
                    (
                        ("url", str),
                        ("naam", str),
                        ("zaak", str),
                        ("eigenschap", str),
                        ("waarde", str),
                    ),
                )

    def test_create_zaakeigenschap_not_in_zaaktypen_fails(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(eigenschapnaam="foobar")
        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak.uuid)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": zaak_url,
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "overlast_water",
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakEigenschapCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create_external_eigenschap(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype)
        zaak_url = reverse(zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(eigenschap, json=get_eigenschap_response(eigenschap, zaaktype))

            response = self.client.post(
                url,
                {
                    "zaak": zaak_url,
                    "eigenschap": eigenschap,
                    "waarde": "overlast_water",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_eigenschap_fail_bad_url(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        response = self.client.post(
            url, {"zaak": zaak_url, "eigenschap": "abcd", "waarde": "overlast_water",},
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_resultaattype_fail_not_json_url(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "eigenschap": "http://example.com",
                "waarde": "overlast_water",
            },
        )

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_resultaattype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype)
        zaak_url = reverse(zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(eigenschap, json={"url": eigenschap, "zaaktype": zaaktype})

            response = self.client.post(
                url,
                {
                    "zaak": zaak_url,
                    "eigenschap": eigenschap,
                    "waarde": "overlast_water",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_resultaattype_fail_zaaktype_mismatch(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype1)
        zaak_url = reverse(zaak)
        url = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak.uuid)

        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaaktype1, json=get_zaaktype_response(catalogus, zaaktype1))
            m.get(zaaktype2, json=get_zaaktype_response(catalogus, zaaktype2))
            m.get(eigenschap, json=get_eigenschap_response(eigenschap, zaaktype2))

            response = self.client.post(
                url,
                {
                    "zaak": zaak_url,
                    "eigenschap": eigenschap,
                    "waarde": "overlast_water",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")
