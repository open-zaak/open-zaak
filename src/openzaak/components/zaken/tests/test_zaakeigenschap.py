# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
"""
Als behandelaar wil ik locatie- en/of objectinformatie bij de melding
ontvangen, zodat ik voldoende details weet om de melding op te volgen.

ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/52
"""
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.constants import FormaatChoices
from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ZaakTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import ZaakEigenschap
from .factories import ZaakEigenschapFactory, ZaakFactory
from .utils import get_eigenschap_response, get_zaaktype_response


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class US52TestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zet_eigenschappen(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(
            eigenschapnaam="foobar", zaaktype=zaak.zaaktype
        )
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})
        zaak_url = reverse(zaak)
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
        detail_url = reverse(zaakeigenschap, kwargs={"zaak_uuid": zaak.uuid})
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
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

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
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})
        zaak_url = reverse(zaak)
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

    def test_zaak_eigenschappen_update(self):
        zaak = ZaakFactory.create()
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak,
            waarde="This is a value",
            eigenschap__specificatie_van_eigenschap__lengte=30,
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak.uuid},
        )
        zaak_url = reverse(zaak)

        zaakeigenschap_data = {
            "zaak": f"http://testserver{zaak_url}",
            "eigenschap": f"http://testserver{reverse(zaakeigenschap.eigenschap)}",
            "waarde": "This is a changed value",
        }

        response = self.client.put(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_zaak_eigenschappen_partial_update(self):
        zaak = ZaakFactory.create()
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak,
            waarde="This is a value",
            eigenschap__specificatie_van_eigenschap__lengte=30,
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak.uuid},
        )
        zaak_url = reverse(
            "zaak-detail",
            kwargs={"version": 1, "uuid": zaak.uuid},
        )

        zaakeigenschap_data = {
            "zaak": f"http://testserver{zaak_url}",
            "eigenschap": f"http://testserver{reverse(zaakeigenschap.eigenschap)}",
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_zaak_eigenschappen_partial_update_without_eigenschap(self):
        zaak = ZaakFactory.create()
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak,
            waarde="This is a value",
            eigenschap__specificatie_van_eigenschap__lengte=30,
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak.uuid},
        )

        zaakeigenschap_data = {
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_cannot_change_eigenschap(self):
        zaak = ZaakFactory.create()
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak.uuid},
        )
        zaak_url = reverse(
            "zaak-detail",
            kwargs={"version": 1, "uuid": zaak.uuid},
        )

        eigenschap = EigenschapFactory()

        zaakeigenschap_data = {
            "zaak": f"http://testserver{zaak_url}",
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        invalid_params = response.json()["invalidParams"]

        self.assertEqual(1, len(invalid_params))

        self.assertEqual("eigenschap", invalid_params[0]["name"])
        self.assertEqual("wijzigen-niet-toegelaten", invalid_params[0]["code"])

    def test_cannot_change_zaak(self):
        zaak1 = ZaakFactory.create()
        zaak2 = ZaakFactory.create(zaaktype=zaak1.zaaktype)
        eigenschap = EigenschapFactory(zaaktype=zaak1.zaaktype)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak1, eigenschap=eigenschap, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak1.uuid},
        )
        zaak2_url = reverse(zaak2)

        zaakeigenschap_data = {
            "zaak": f"http://openzaak.nl{zaak2_url}",
            "eigenschap": f"http://openzaak.nl{reverse(eigenschap)}",
            "waarde": "This is a changed value",
        }

        response = self.client.patch(
            zaakeigenschap_url,
            data=zaakeigenschap_data,
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        invalid_params = response.json()["invalidParams"]

        self.assertEqual(1, len(invalid_params))
        self.assertIn("zaak", invalid_params[0]["name"])
        self.assertEqual("wijzigen-niet-toegelaten", invalid_params[0]["code"])

    def test_delete(self):
        zaak = ZaakFactory.create()
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaak.uuid},
        )

        self.assertEqual(1, ZaakEigenschap.objects.all().count())

        response = self.client.delete(zaakeigenschap_url)

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(0, ZaakEigenschap.objects.all().count())


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakEigenschapCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

    def test_create_external_eigenschap(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype)
        zaak_url = reverse(zaak)
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
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
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "eigenschap": "abcd",
                "waarde": "overlast_water",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_eigenschap_fail_not_json_url(self):
        ServiceFactory.create(api_root="http://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                url,
                {
                    "zaak": zaak_url,
                    "eigenschap": "http://example.com/",
                    "waarde": "overlast_water",
                },
            )

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_eigenschap_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype)
        zaak_url = reverse(zaak)
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
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

    def test_create_external_eigenschap_fail_zaaktype_mismatch(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        eigenschap = "https://externe.catalogus.nl/api/v1/eigenschappen/7a3e4a22-d789-4381-939b-401dbce29426"

        zaak = ZaakFactory(zaaktype=zaaktype1)
        zaak_url = reverse(zaak)
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
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

    def test_create_external_eigenschap_fail_unknown_service(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(
            url,
            {
                "zaak": zaak_url,
                "eigenschap": "https://other-externe.catalogus.nl/api/v1/eigenschappen/1",
                "waarde": "overlast_water",
            },
        )

        error = get_validation_errors(response, "eigenschap")
        self.assertEqual(error["code"], "unknown-service")


class ZaakEigenschapJWTExpiryTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @freeze_time("2019-01-01T12:00:00")
    def setUp(self):
        super().setUp()
        token = generate_jwt(
            self.client_id,
            self.secret,
            self.user_id,
            self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_zaakeigenschap_list_jwt_expired(self):
        zaak = ZaakFactory.create()
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_zaakeigenschap_detail_jwt_expired(self):
        zaakeigenschap = ZaakEigenschapFactory.create()
        url = reverse(
            zaakeigenschap,
            kwargs={"zaak_uuid": zaakeigenschap.zaak.uuid},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_zaakeigenschap_create_jwt_expired(self):
        zaak = ZaakFactory.create()
        eigenschap = EigenschapFactory.create(eigenschapnaam="foobar")
        url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid})
        zaak_url = reverse(zaak)
        eigenschap_url = reverse(eigenschap)
        data = {
            "zaak": zaak_url,
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "overlast_water",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")


@override_settings(ZAAK_EIGENSCHAP_WAARDE_VALIDATION=True)
class ZaakEigenschapWaardeTests(JWTAuthMixin, APITestCase):
    """
    test that `waarde` is validated against `eigenschap.specificatie`
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)

        cls.url = reverse(ZaakEigenschap, kwargs={"zaak_uuid": cls.zaak.uuid})
        cls.zaak_url = f"http://testserver{reverse(cls.zaak)}"

    def test_string_valid(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__lengte="10",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "some text",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_string_incorrect_length(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__lengte="4",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "some text",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    def test_string_in_enum(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__waardenverzameling=["some", "other"],
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "some",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_string_not_in_enum(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__waardenverzameling=["some", "other"],
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "text",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    def test_number_valid(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.getal,
            specificatie_van_eigenschap__lengte="3",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "4",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_number_with_fractional_valid(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.getal,
            specificatie_van_eigenschap__lengte="3,1",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "14,5",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_number_incorrect_format(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.getal,
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "aaaa",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    def test_number_incorrect_length(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.getal,
            specificatie_van_eigenschap__lengte="3",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "4444",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    def test_date_valid(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.datum,
            specificatie_van_eigenschap__lengte="8",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "20201201",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_date_incorrect_format(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.datum,
            specificatie_van_eigenschap__lengte="8",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "2020-12-01",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    def test_datetime_valid(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.datum_tijd,
            specificatie_van_eigenschap__lengte="14",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "20201201155555",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_datetime_incorrect_format(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.datum_tijd,
            specificatie_van_eigenschap__lengte="14",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "2020-12-01T15:55:55",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "waarde-incorrect-format")

    @override_settings(ZAAK_EIGENSCHAP_WAARDE_VALIDATION=False)
    def test_incorrect_but_env_var_false(self):
        eigenschap = EigenschapFactory.create(
            zaaktype=self.zaaktype,
            specificatie_van_eigenschap__formaat=FormaatChoices.tekst,
            specificatie_van_eigenschap__lengte="4",
        )
        data = {
            "zaak": self.zaak_url,
            "eigenschap": f"http://testserver{reverse(eigenschap)}",
            "waarde": "some text",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
