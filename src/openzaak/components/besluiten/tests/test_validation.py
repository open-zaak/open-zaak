# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from vng_api_common.validators import IsImmutableValidator, UntilTodayValidator

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.tests import JWTAuthMixin

from .factories import BesluitFactory


class BesluitValidationTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("besluit-list")
    heeft_alle_autorisaties = True

    def test_rsin_invalid(self):
        cases = [
            ("1234567", "invalid-length"),
            ("12345678", "invalid-length"),
            ("123456789", "invalid"),
        ]

        for rsin, error_code in cases:
            with self.subTest(rsin=rsin, error_code=error_code):
                response = self.client.post(
                    self.url, {"verantwoordelijkeOrganisatie": rsin}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                error = get_validation_errors(response, "verantwoordelijkeOrganisatie")
                self.assertEqual(error["code"], error_code)

    @freeze_time("2018-09-06T12:08+0200")
    def test_future_datum(self):
        response = self.client.post(self.url, {"datum": "2018-09-07"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "datum")
        self.assertEqual(error["code"], UntilTodayValidator.code)

    def test_duplicate_rsin_identificatie(self):
        besluit = BesluitFactory.create(
            identificatie="123456", besluittype__concept=False
        )
        besluittype_url = reverse(besluit.besluittype)

        response = self.client.post(
            self.url,
            {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "identificatie": "123456",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2018-09-06",
                "ingangsdatum": "2018-10-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "identificatie")
        self.assertEqual(error["code"], "identificatie-niet-uniek")

    def test_change_immutable_fields(self):
        besluit = BesluitFactory.create(identificatie="123456")
        besluit2 = BesluitFactory.create(identificatie="123456")

        url = reverse(besluit)

        response = self.client.patch(
            url,
            {
                "verantwoordelijkeOrganisatie": besluit2.verantwoordelijke_organisatie,
                "identificatie": "123456789",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        identificatie_error = get_validation_errors(response, "identificatie")
        self.assertEqual(identificatie_error["code"], IsImmutableValidator.code)

        verantwoordelijke_organisatie_error = get_validation_errors(
            response, "verantwoordelijkeOrganisatie"
        )
        self.assertEqual(
            verantwoordelijke_organisatie_error["code"], IsImmutableValidator.code
        )

    def test_validate_besluittype_valid(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = reverse("besluit-list")

        response = self.client.post(
            url,
            {
                "verantwoordelijkeOrganisatie": "000000000",
                "identificatie": "123456",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2018-09-06",
                "ingangsdatum": "2018-10-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_besluittype_invalid(self):
        list_url = reverse("besluit-list")

        with requests_mock.Mocker() as m:
            m.get("https://example.com/zrc/zaken/1234", status_code=404)

            response = self.client.post(
                list_url,
                {
                    "verantwoordelijkeOrganisatie": "000000000",
                    "identificatie": "123456",
                    "besluittype": "https://example.com/zrc/zaken/1234",
                    "datum": "2018-09-06",
                    "ingangsdatum": "2018-10-01",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "bad-url")

    def test_besluittype_unpublished(self):
        besluittype = BesluitTypeFactory.create()
        besluittype_url = reverse(besluittype)
        url = reverse("besluit-list")

        response = self.client.post(
            url,
            {
                "verantwoordelijkeOrganisatie": "000000000",
                "identificatie": "123456",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2018-09-06",
                "ingangsdatum": "2018-10-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "not-published")

    def test_zaaktype_besluittype_relation(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)
        besluittype.zaaktypen.add(zaak.zaaktype)
        list_url = reverse("besluit-list")

        response = self.client.post(
            list_url,
            {
                "verantwoordelijkeOrganisatie": "000000000",
                "identificatie": "123456",
                "besluittype": f"http://testserver{besluittype_url}",
                "zaak": f"http://testserver{zaak_url}",
                "datum": "2018-09-06",
                "ingangsdatum": "2018-10-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_no_zaaktype_besluittype_relation(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        list_url = reverse("besluit-list")

        response = self.client.post(
            list_url,
            {
                "verantwoordelijkeOrganisatie": "000000000",
                "identificatie": "123456",
                "besluittype": f"http://testserver{besluittype_url}",
                "zaak": f"http://testserver{zaak_url}",
                "datum": "2018-09-06",
                "ingangsdatum": "2018-10-01",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_update(self):
        besluit = BesluitFactory.create(besluittype__concept=False)
        besluit_url = reverse(besluit)

        besluittype_url = reverse(besluit.besluittype)
        response = self.client.put(
            besluit_url,
            {
                "identificatie": besluit.identificatie,
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "datum": "2019-01-01",
                "ingangsdatum": "2018-01-01",
                "besluittype": f"http://testserver{besluittype_url}",
                "toelichting": "aangepast",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["toelichting"], "aangepast")

        besluit.refresh_from_db()
        self.assertEqual(besluit.toelichting, "aangepast")

    def test_update_besluittype_fails(self):
        besluit = BesluitFactory.create()
        besluit_url = reverse(besluit)

        besluittype = BesluitTypeFactory.create()
        besluittype_url = reverse(besluittype)
        response = self.client.patch(
            besluit_url, {"besluittype": f"http://testserver{besluittype_url}"}
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], IsImmutableValidator.code)


class BesluitInformatieObjectTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_validate_informatieobject_invalid(self):
        besluit = BesluitFactory.create()
        besluit_url = reverse("besluit-detail", kwargs={"uuid": besluit.uuid})
        url = reverse("besluitinformatieobject-list")

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": "https://foo.bar/123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "bad-url")

    def test_validate_no_informatieobjecttype_besluittype_relation(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        besluit_url = reverse(besluit)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        url = reverse("besluitinformatieobject-list")

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-besluittype-informatieobjecttype-relation"
        )
