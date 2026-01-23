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

from ..models import Zaak, ZaakRelatie
from .factories import ZaakFactory, ZaakRelatieFactory
from .utils import ZAAK_READ_KWARGS, ZAAK_WRITE_KWARGS, get_zaak_response


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "testserver.com"])
class ExternalGerelateerdeZakenTestsTestCase(JWTAuthMixin, APITestCase):
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

    def test_create_external_gerelateerde_zaak(self):
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
                    "gerelateerdeZaken": [
                        {
                            "url": zaak_external,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # Relationship is not created both ways, because the other zaak is external
        self.assertEqual(ZaakRelatie.objects.count(), 1)

        relation = ZaakRelatie.objects.get()

        self.assertEqual(relation._gerelateerde_zaak_url, zaak_external)

    def test_create_external_gerelateerde_zaak_does_not_create_duplicate_relations(
        self,
    ):
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
                    "gerelateerdeZaken": [
                        {
                            "url": zaak_external,
                        },
                        {
                            "url": zaak_external,
                        },
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # Relationship is not created both ways, because the other zaak is external
        self.assertEqual(ZaakRelatie.objects.count(), 1)

        relation = ZaakRelatie.objects.get()

        self.assertEqual(relation._gerelateerde_zaak_url, zaak_external)

    def test_create_external_gerelateerde_zaak_without_setting_gerelateerde_zaak_typen(
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
                    "gerelateerdeZaken": [
                        {
                            "url": zaak_external,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": zaak_external,
                }
            ],
        )

    def test_create_external_gerelateerde_zaak_fail_bad_url(self):
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
                "gerelateerdeZaken": [
                    {
                        "url": "abcd",
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "gerelateerdeZaken.0.url")
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
                    "gerelateerdeZaken": [
                        {
                            "url": " http://example.com/",
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "gerelateerdeZaken.0.url")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_gerelateerde_zaak_fail_invalid_schema(self):
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
                    "gerelateerdeZaken": [
                        {
                            "url": zaak_external,
                        }
                    ],
                },
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "gerelateerdeZaken.0.url")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_gerelateerde_zaak_fail_unknown_service(self):
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
                "gerelateerdeZaken": [
                    {
                        "url": "https://other-externe.zaken.nl/api/v1/zaken/1",
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "gerelateerdeZaken.0.url")
        self.assertEqual(error["code"], "unknown-service")

    def test_update_make_gerelateerde_zaken_empty(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        zaaktype_url = f"http://testserver.com{reverse(zaaktype)}"
        zaak_external = (
            "https://externe.zaken.nl/api/v1/zaken/a620b183-d898-4576-ae94-3f21d43cc576"
        )

        ZaakRelatieFactory.create(zaak=zaak, url=zaak_external)

        with requests_mock.Mocker() as m:
            mock_zrc_oas_get(m)
            m.get(zaak_external, json=get_zaak_response(zaak_external, zaaktype_url))

            response = self.client.patch(
                zaak_url,
                {"gerelateerdeZaken": []},
                **ZAAK_WRITE_KWARGS,
                HTTP_HOST="testserver.com",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(
                response.json()["gerelateerdeZaken"],
                [],
            )
            self.assertEqual(ZaakRelatie.objects.count(), 0)


@override_settings(ALLOWED_HOSTS=["testserver", "testserver.com"])
class LocalGerelateerdeZakenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy(Zaak)

    def test_create_local_gerelateerde_zaak(self):
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
                "gerelateerdeZaken": [
                    {
                        "url": zaak_url,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": zaak_url,
                }
            ],
        )
        self.assertEqual(ZaakRelatie.objects.count(), 2)

        relation, reverse_relation = ZaakRelatie.objects.order_by("pk")

        # Relationship should be created bothways
        self.assertEqual(relation._gerelateerde_zaak, zaak)
        self.assertEqual(reverse_relation.zaak, zaak)

    def test_create_local_gerelateerde_zaak_does_not_create_duplicate_relations(self):
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
                "gerelateerdeZaken": [
                    {
                        "url": zaak_url,
                    },
                    {
                        "url": zaak_url,
                    },
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": zaak_url,
                }
            ],
        )
        self.assertEqual(ZaakRelatie.objects.count(), 2)

        relation, reverse_relation = ZaakRelatie.objects.order_by("pk")

        # Relationship should be created bothways
        self.assertEqual(relation._gerelateerde_zaak, zaak)
        self.assertEqual(reverse_relation.zaak, zaak)

    def test_create_local_gerelateerde_zaak_invalid_url(self):
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
                "gerelateerdeZaken": [
                    {
                        "url": "invalid",
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "gerelateerdeZaken.0.url")

        self.assertEqual(error["code"], "bad-url")

    def test_create_local_gerelateerde_zaak_without_setting_gerelateerde_zaak_typen(
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
                "gerelateerdeZaken": [
                    {
                        "url": zaak_url,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": zaak_url,
                }
            ],
        )

    def test_read_local_gerelateerde_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        gerelateerde_zaak = ZaakFactory.create(zaaktype=zaaktype)
        gerelateerde_zaak_url = f"http://testserver.com{reverse(gerelateerde_zaak)}"

        ZaakRelatieFactory.create(zaak=zaak, url=gerelateerde_zaak)

        response = self.client.get(
            zaak_url, **ZAAK_READ_KWARGS, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": gerelateerde_zaak_url,
                }
            ],
        )

    def test_read_local_gerelateerde_zaak_reflexivity(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        gerelateerde_zaak = ZaakFactory.create(zaaktype=zaaktype)
        gerelateerde_zaak_url = f"http://testserver.com{reverse(gerelateerde_zaak)}"

        gerelateerde_zaak_reverse = ZaakFactory.create(zaaktype=zaaktype)
        gerelateerde_zaak_reverse_url = (
            f"http://testserver.com{reverse(gerelateerde_zaak_reverse)}"
        )

        ZaakRelatieFactory.create(zaak=zaak, url=gerelateerde_zaak)
        ZaakRelatieFactory.create(zaak=gerelateerde_zaak_reverse, url=zaak)

        response = self.client.get(
            zaak_url, **ZAAK_READ_KWARGS, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": gerelateerde_zaak_url,
                },
                {
                    "url": gerelateerde_zaak_reverse_url,
                },
            ],
        )

    def test_update_local_gerelateerde_zaak(self):
        zaak = ZaakFactory.create()
        related_zaak = ZaakFactory.create()
        zaak_url = f"http://testserver.com{reverse(zaak)}"
        related_zaak_url = f"http://testserver.com{reverse(related_zaak)}"

        response = self.client.patch(
            zaak_url,
            {
                "gerelateerdeZaken": [
                    {
                        "url": related_zaak_url,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {
                    "url": related_zaak_url,
                }
            ],
        )

    def test_update_change_gerelateerde_zaken(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        gerelateerde_zaak = ZaakFactory.create(zaaktype=zaaktype)
        ZaakRelatieFactory.create(zaak=zaak, url=gerelateerde_zaak)

        other_zaak = ZaakFactory.create(zaaktype=zaaktype)
        other_zaak_url = f"http://testserver.com{reverse(other_zaak)}"

        response = self.client.patch(
            zaak_url,
            {"gerelateerdeZaken": [{"url": other_zaak_url}]},
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [{"url": other_zaak_url}],
        )
        self.assertEqual(ZaakRelatie.objects.count(), 2)

        relation, reverse_relation = ZaakRelatie.objects.order_by("pk")

        # Relationship should be created bothways
        self.assertEqual(relation.zaak, zaak)
        self.assertEqual(relation._gerelateerde_zaak, other_zaak)
        self.assertEqual(reverse_relation.zaak, other_zaak)
        self.assertEqual(reverse_relation._gerelateerde_zaak, zaak)

    def test_update_gerelateerde_zaken_add_extra(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        gerelateerde_zaak = ZaakFactory.create(zaaktype=zaaktype)
        ZaakRelatieFactory.create(zaak=zaak, url=gerelateerde_zaak)

        other_zaak = ZaakFactory.create(zaaktype=zaaktype)

        response = self.client.patch(
            zaak_url,
            {
                "gerelateerdeZaken": [
                    {"url": f"http://testserver.com{reverse(gerelateerde_zaak)}"},
                    {"url": f"http://testserver.com{reverse(other_zaak)}"},
                ]
            },
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [
                {"url": f"http://testserver.com{reverse(gerelateerde_zaak)}"},
                {"url": f"http://testserver.com{reverse(other_zaak)}"},
            ],
        )
        self.assertEqual(ZaakRelatie.objects.count(), 4)

        # Relationships should be created bothways
        relation1, reverse_relation1, relation2, reverse_relation2 = (
            ZaakRelatie.objects.order_by("pk")
        )

        # Relation that existed before the update is preserved
        self.assertEqual(relation1.zaak, zaak)
        self.assertEqual(relation1._gerelateerde_zaak, gerelateerde_zaak)
        self.assertEqual(reverse_relation1.zaak, gerelateerde_zaak)
        self.assertEqual(reverse_relation1._gerelateerde_zaak, zaak)

        # New relation is created
        self.assertEqual(relation2.zaak, zaak)
        self.assertEqual(relation2._gerelateerde_zaak, other_zaak)
        self.assertEqual(reverse_relation2.zaak, other_zaak)
        self.assertEqual(reverse_relation2._gerelateerde_zaak, zaak)

    def test_update_make_gerelateerde_zaken_empty(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://testserver.com{reverse(zaak)}"

        gerelateerde_zaak = ZaakFactory.create(zaaktype=zaaktype)
        ZaakRelatieFactory.create(zaak=zaak, url=gerelateerde_zaak)

        response = self.client.patch(
            zaak_url,
            {"gerelateerdeZaken": []},
            **ZAAK_WRITE_KWARGS,
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["gerelateerdeZaken"],
            [],
        )
        self.assertEqual(ZaakRelatie.objects.count(), 0)
