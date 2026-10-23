# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
)
from openzaak.components.besluiten.models import Besluit
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.besluiten.tests.utils import get_besluit_response
from openzaak.components.catalogi.tests.factories import (
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import ZaakBesluit
from openzaak.components.zaken.tests.utils import ZAAK_READ_KWARGS
from openzaak.tests.utils import JWTAuthMixin, mock_brc_oas_get

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE
from .factories import (
    ZaakFactory,
)


class BesluitenSignals(APITestCase):
    def test_create_besluit_without_zaak(self):
        BesluitFactory.create(for_zaak=False)

        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_create_besluit_with_zaak(self):
        besluit = BesluitFactory.create(for_zaak=True)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        zaakbesluit = ZaakBesluit.objects.get()

        self.assertEqual(zaakbesluit.besluit, besluit)
        self.assertEqual(zaakbesluit.zaak, besluit.zaak)

    def test_create_besluit_with_zaak_raw(self):
        besluit = BesluitFactory.create(for_zaak=True)
        pk = besluit.pk
        besluit.delete()
        self.assertEqual(ZaakBesluit.objects.count(), 0)
        besluit.pk = pk

        besluit.save_base(raw=True, force_insert=True)

        self.assertTrue(Besluit.objects.filter(pk=pk).exists())
        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_delete_besluit_without_zaak(self):
        besluit = BesluitFactory.create(for_zaak=False)

        self.assertEqual(ZaakBesluit.objects.count(), 0)

        besluit.delete()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_delete_besluit_with_zaak(self):
        besluit = BesluitFactory.create(for_zaak=True)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        besluit.delete()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_update_besluit_without_zaak(self):
        besluit = BesluitFactory.create(for_zaak=False)

        self.assertEqual(ZaakBesluit.objects.count(), 0)

        besluit.toelichting = "new desc"
        besluit.save()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_update_besluit_add_zaak(self):
        besluit = BesluitFactory.create(for_zaak=False)

        self.assertEqual(ZaakBesluit.objects.count(), 0)

        zaak = ZaakFactory.create()
        besluit.zaak = zaak
        besluit.save()

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        zaakbesluit = ZaakBesluit.objects.get()

        self.assertEqual(zaakbesluit.besluit, besluit)
        self.assertEqual(zaakbesluit.zaak, besluit.zaak)

    def test_update_besluit_remove_zaak(self):
        besluit = BesluitFactory.create(for_zaak=True)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        besluit.zaak = None
        besluit.save()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

    def test_update_besluit_change_zaak(self):
        besluit = BesluitFactory.create(for_zaak=True)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        zaakbesluit_old = ZaakBesluit.objects.get()

        self.assertEqual(zaakbesluit_old.besluit, besluit)
        self.assertEqual(zaakbesluit_old.zaak, besluit.zaak)

        zaak_new = ZaakFactory.create()
        besluit.zaak = zaak_new
        besluit.save()

        zaakbesluit_new = ZaakBesluit.objects.get()

        self.assertNotEqual(zaakbesluit_old.id, zaakbesluit_new.id)
        self.assertEqual(zaakbesluit_new.zaak, zaak_new)


class InternalZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list(self):
        """
        Assert that it's possible to list besluiten for zaken.
        """
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        # get ZaakBesluit created via signals
        zaakbesluit = ZaakBesluit.objects.get()
        zaakbesluit_url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
        )
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "_expand": {},
                    "url": f"http://testserver{zaakbesluit_url}",
                    "uuid": str(zaakbesluit.uuid),
                    "besluit": f"http://testserver{reverse(besluit)}",
                }
            ],
        )

    def test_detail(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        # get ZaakBesluit created via signals
        zaakbesluit = ZaakBesluit.objects.get()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "_expand": {},
                "url": f"http://testserver{url}",
                "uuid": str(zaakbesluit.uuid),
                "besluit": f"http://testserver{reverse(besluit)}",
            },
        )

    def test_create(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)

        self.assertEqual(ZaakBesluit.objects.count(), 1)

        besluit_url = reverse(besluit)
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(url, {"besluit": f"http://testserver{besluit_url}"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ZaakBesluit.objects.count(), 1)

    def test_delete(self):
        besluit = BesluitFactory.create(for_zaak=True)
        zaakbesluit = ZaakBesluit.objects.get()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaakbesluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )
        besluit.zaak = None
        besluit.save()

        self.assertEqual(ZaakBesluit.objects.count(), 0)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_while_relation_exists_fails(self):
        BesluitFactory.create(for_zaak=True)
        zaakbesluit = ZaakBesluit.objects.get()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaakbesluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "inconsistent-relation")

    def test_delete_while_relation_does_not_exist(self):
        besluit = BesluitFactory.create(for_zaak=False)
        zaak = ZaakFactory.create()
        zaakbesluit = ZaakBesluit.objects.create(zaak=zaak, besluit=besluit)
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": zaakbesluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(ZaakBesluit.objects.exists())


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalZaakBesluitTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    besluit = "https://externe.catalogus.nl/api/v1/besluiten/b71f72ef-198d-44d8-af64-ae1932df830a"
    besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/7ef7d016-b766-4456-a90c-8908eeb19b49"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.brc
        )

    def test_create(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            mock_brc_oas_get(m)
            m.get(
                self.besluit,
                json=get_besluit_response(self.besluit, self.besluittype, zaak_url),
            )

            response = self.client.post(url, data={"besluit": self.besluit})

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

            zaakbesluit = ZaakBesluit.objects.get()

            self.assertEqual(zaakbesluit.zaak, zaak)
            self.assertEqual(zaakbesluit.besluit, self.besluit)

    def test_delete(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://testserver{reverse(zaak)}"

        with requests_mock.Mocker() as m:
            mock_brc_oas_get(m)
            m.get(
                self.besluit,
                json=get_besluit_response(self.besluit, self.besluittype, zaak_url),
            )

            zaakbesluit = ZaakBesluit.objects.create(zaak=zaak, besluit=self.besluit)
            url = reverse(
                "zaakbesluit-detail",
                kwargs={"zaak_uuid": zaak.uuid, "uuid": zaakbesluit.uuid},
            )

            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ZaakBesluitenJWTExpiryTests(JWTAuthMixin, APITestCase):
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
    def test_zaakbesluit_list_jwt_expired(self):
        zaak = ZaakFactory.create()
        url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_zaakbesluit_detail_jwt_expired(self):
        besluit = BesluitFactory.create(for_zaak=True)
        zaakbesluit = besluit.zaak.zaakbesluit_set.first()
        url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": besluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")


@tag("expand")
class ZaakInformatieObjectenExpandTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.besluit = BesluitFactory.create(for_zaak=True)
        cls.zaakbesluit = ZaakBesluit.objects.get(
            besluit=cls.besluit, zaak=cls.besluit.zaak
        )

        cls.url = reverse(
            "zaakbesluit-list",
            kwargs={"zaak_uuid": cls.besluit.zaak.uuid},
        )

    def get_resource(self, resource):
        """Resource without `_expand`"""
        response = self.client.get(reverse(resource), **ZAAK_READ_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # The detail responses also include the _expand attribute, but the list response
        # only has a _expand attribute at the root level (no _expand nested inside _expand)
        data.pop("_expand", None)
        return data

    def test_besluit_list_expand_include_all_resources_with_query_count(self):
        zaakbesluit_url = f"{self.host_prefix}{self.url}/{self.zaakbesluit.uuid}"
        expected_result = [
            {
                "url": zaakbesluit_url,
                "uuid": str(self.zaakbesluit.uuid),
                "besluit": self.check_for_instance(self.besluit),
                "_expand": {
                    "besluit": self.get_resource(self.besluit),
                },
            }
        ]

        with self.assertNumQueries(18):
            response = self.client.get(
                self.url,
                {"expand": "besluit"},
                **ZAAK_READ_KWARGS,
            )
            data = response.json()
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(data, expected_result)

    def test_invalid_expansion(self):
        for expand in ("unknown", "besluit.unknown", "zaak"):
            with self.subTest(expand=expand):
                response = self.client.get(
                    self.url, {"expand": expand}, **ZAAK_READ_KWARGS
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    get_validation_errors(response, "expand")["code"],
                    "invalid_choice",
                )


@tag("expand-authorization")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakBesluitenIncludePermissionsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = False

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)
        cls.besluit = BesluitFactory.create(zaak=cls.zaak)
        cls.zaakbesluit = ZaakBesluit.objects.get(zaak=cls.zaak, besluit=cls.besluit)
        cls.list_url = reverse("zaakbesluit-list", kwargs={"zaak_uuid": cls.zaak.uuid})
        cls.detail_url = reverse(
            "zaakbesluit-detail",
            kwargs={"zaak_uuid": cls.zaak.uuid, "uuid": cls.zaakbesluit.uuid},
        )
        super().setUpTestData()

    def test_expand_besluit_permissions(self):
        """Expanding besluit requires SCOPE_BESLUITEN_ALLES_LEZEN"""
        params = {"expand": "besluit"}
        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                # No scopes access is denied
                self.autorisatie.scopes = []
                self.autorisatie.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # SCOPE_ZAKEN_CREATE does not grant access
                self.autorisatie.scopes = [SCOPE_ZAKEN_CREATE]
                self.autorisatie.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # SCOPE_ZAKEN_ALLES_LEZEN permits access to its own resource
                self.autorisatie.scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
                self.autorisatie.save()
                response = self.client.get(url, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # Besluiten expansion requires SCOPE_BESLUITEN_ALLES_LEZEN
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # Only SCOPE_BESLUITEN_AANMAKEN is insufficient.
                besluiten_auth = Autorisatie.objects.create(
                    applicatie=self.applicatie,
                    component=ComponentTypes.brc,
                    scopes=[SCOPE_BESLUITEN_AANMAKEN],
                )
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                # Adding SCOPE_BESLUITEN_ALLES_LEZEN access permits the expansion
                besluiten_auth.scopes = [SCOPE_BESLUITEN_ALLES_LEZEN]
                besluiten_auth.save()
                response = self.client.get(url, params, **ZAAK_READ_KWARGS)
                besluiten_auth.delete()  # remove auth for the next use

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()
                if url == self.list_url:
                    data = data[0]
                self.assertIn("besluit", data["_expand"])
