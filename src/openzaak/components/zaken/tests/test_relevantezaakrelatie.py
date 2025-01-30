# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.tests.utils import JWTAuthMixin, mock_zrc_oas_get

from ..constants import AardZaakRelatie
from ..models import Zaak
from .factories import RelevanteZaakRelatieFactory, ZaakFactory
from .utils import ZAAK_READ_KWARGS, ZAAK_WRITE_KWARGS, get_zaak_response


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "testserver.com"])
class ExternalRelevanteZakenTestsTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True
    list_url = reverse_lazy(Zaak)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.zaken.nl/api/v1/",
            api_type=APITypes.zrc,
        )
        ServiceFactory.create(
            api_root="http://testserver.com/catalogi/api/v1/",
            api_type=APITypes.ztc,
        )

    def test_create_external_relevante_andere_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak_external = (
            "https://externe.zaken.nl/api/v1/zaken/a620b183-d898-4576-ae94-3f21d43cc576"
        )

        with requests_mock.Mocker() as m:
            mock_zrc_oas_get(m)
            m.get(zaak_external, json=get_zaak_response(zaak_external, zaaktype_url))

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype_url,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "relevanteAndereZaken": [
                        {
                            "url": zaak_external,
                            "aardRelatie": AardZaakRelatie.vervolg,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_relevante_andere_zaak_without_setting_gerelateerde_zaak_typen(
        self,
    ):
        zaak_external = (
            "https://externe.zaken.nl/api/v1/zaken/a620b183-d898-4576-ae94-3f21d43cc576"
        )

        zaaktype_1 = ZaakTypeFactory.create(concept=False)
        zaaktype_url_1 = f"http://testserver.com{reverse(zaaktype_1)}"

        zaaktype_2 = ZaakTypeFactory.create(concept=False)
        zaaktype_url_2 = f"http://testserver.com{reverse(zaaktype_2)}"

        # gerelateerde_zaak_typen are not set.
        self.assertEqual(zaaktype_1.zaaktypenrelaties.count(), 0)

        with requests_mock.Mocker() as m:
            mock_zrc_oas_get(m)
            m.get(zaak_external, json=get_zaak_response(zaak_external, zaaktype_url_1))

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype_url_2,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "relevanteAndereZaken": [
                        {
                            "url": zaak_external,
                            "aardRelatie": AardZaakRelatie.vervolg,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["relevanteAndereZaken"],
            [
                {
                    "url": zaak_external,
                    "aardRelatie": AardZaakRelatie.vervolg,
                    "overigeRelatie": "",
                    "toelichting": "",
                }
            ],
        )

    def test_create_external_relevante_zaak_fail_bad_url(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": "abcd",
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "relevanteAndereZaken.0.url")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_relevante_zaak_fail_no_json_url(self):
        ServiceFactory.create(
            api_root="http://example.com/",
            api_type=APITypes.zrc,
        )
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype_url,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "relevanteAndereZaken": [
                        {
                            "url": " http://example.com/",
                            "aardRelatie": AardZaakRelatie.vervolg,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "relevanteAndereZaken.0.url")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_relevante_zaak_fail_invalid_schema(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak_external = (
            "https://externe.zaken.nl/api/v1/zaken/a620b183-d898-4576-ae94-3f21d43cc576"
        )
        zaak_data = {
            "url": zaak_external,
            "uuid": "d781cd1b-f100-4051-9543-153b93299da4",
            "identificatie": "ZAAK-2019-0000000001",
            "bronorganisatie": "517439943",
            "omschrijving": "some zaak",
            "zaaktype": zaaktype_url,
        }

        with requests_mock.Mocker() as m:
            mock_zrc_oas_get(m)
            m.get(zaak_external, json=zaak_data)

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype_url,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "relevanteAndereZaken": [
                        {
                            "url": zaak_external,
                            "aardRelatie": AardZaakRelatie.vervolg,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "relevanteAndereZaken.0.url")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_relevante_zaak_fail_unknown_service(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": "https://other-externe.zaken.nl/api/v1/zaken/1",
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "relevanteAndereZaken.0.url")
        self.assertEqual(error["code"], "unknown-service")


@override_settings(ALLOWED_HOSTS=["testserver", "testserver.com"])
class LocalRelevanteAndereZakenTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True
    list_url = reverse_lazy(Zaak)

    def test_create_local_relevante_andere_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": zaak_url,
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["relevanteAndereZaken"],
            [
                {
                    "url": zaak_url,
                    "aardRelatie": AardZaakRelatie.vervolg,
                    "overigeRelatie": "",
                    "toelichting": "",
                }
            ],
        )

    def test_create_local_relevante_andere_zaak_with_aard_overig_overige_relatie_and_toelichting(
        self,
    ):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": zaak_url,
                        "aardRelatie": AardZaakRelatie.overig,
                        "overigeRelatie": "Overig",
                        "toelichting": "toelichting op relatie tussen zaken",
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["relevanteAndereZaken"],
            [
                {
                    "url": zaak_url,
                    "aardRelatie": AardZaakRelatie.overig,
                    "overigeRelatie": "Overig",
                    "toelichting": "toelichting op relatie tussen zaken",
                }
            ],
        )

    def test_create_local_relevante_andere_zaak_without_setting_gerelateerde_zaak_typen(
        self,
    ):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        zaaktype_url = (
            f"http://testserver.com{reverse(ZaakTypeFactory.create(concept=False))}"
        )

        # gerelateerde_zaak_typen are not set.
        self.assertEqual(zaaktype.zaaktypenrelaties.count(), 0)

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": zaak_url,
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["relevanteAndereZaken"],
            [
                {
                    "url": zaak_url,
                    "aardRelatie": AardZaakRelatie.vervolg,
                    "overigeRelatie": "",
                    "toelichting": "",
                }
            ],
        )

    def test_create_local_relevante_andere_zaak_with_aard_overig_without_overige_relatie(
        self,
    ):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        response = self.client.post(
            self.list_url,
            {
                "zaaktype": zaaktype_url,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "relevanteAndereZaken": [
                    {
                        "url": zaak_url,
                        "aardRelatie": AardZaakRelatie.overig,
                        "toelichting": "toelichting op relatie tussen zaken",
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "relevanteAndereZaken.0.overigeRelatie")
        self.assertEqual(error["code"], "overigerelatie-required")

    def test_read_local_relevante_andere_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        relevante_zaak = ZaakFactory.create(zaaktype=zaaktype)
        relevante_zaak_url = f"http://testserver.com{reverse(relevante_zaak)}"

        RelevanteZaakRelatieFactory.create(
            url=relevante_zaak, zaak=zaak, aard_relatie=AardZaakRelatie.vervolg
        )

        response = self.client.get(
            zaak_url, **ZAAK_READ_KWARGS, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["relevanteAndereZaken"],
            [
                {
                    "url": relevante_zaak_url,
                    "aardRelatie": AardZaakRelatie.vervolg,
                    "overigeRelatie": "",
                    "toelichting": "",
                }
            ],
        )
