# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.tests.utils import JWTAuthMixin

from ..models import KlantContact, Resultaat, ZaakInformatieObject, ZaakObject
from .factories import (
    KlantContactFactory,
    ResultaatFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS


class FilterValidationTests(JWTAuthMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_zaak_invalid_filters(self):
        url = reverse("zaak-list")

        invalid_filters = {"zaaktype": "123", "bronorganisatie": "123", "foo": "bar"}

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value}, **ZAAK_WRITE_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rol_invalid_filters(self):
        url = reverse("rol-list")

        invalid_filters = {
            "zaak": "123",  # must be a url
            "betrokkene": "123",  # must be a url
            "betrokkeneType": "not-a-valid-choice",  # must be a pre-defined choice
            "rolomschrijving": "not-a-valid-choice",  # must be a pre-defined choice
            "foo": "bar",
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_invalid_filters(self):
        url = reverse("status-list")

        invalid_filters = {
            "zaak": "123",  # must be a url
            "statustype": "123",  # must be a url
            "foo": "bar",
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_klantcontact_unknown_query_params(self):
        KlantContactFactory.create_batch(2)
        url = reverse(KlantContact)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_resultaat_unknown_query_params(self):
        ResultaatFactory.create_batch(2)
        url = reverse(Resultaat)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_zaakinformatieobject_unknown_query_params(self):
        ZaakInformatieObjectFactory.create_batch(2)
        url = reverse(ZaakInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_zaakobject_unknown_query_params(self):
        ZaakObjectFactory.create_batch(2)
        url = reverse(ZaakObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")
