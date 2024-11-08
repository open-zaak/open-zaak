# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.besluiten.tests.utils import get_besluit_response
from openzaak.tests.utils import JWTAuthMixin, mock_brc_oas_get

from ..models import ZaakBesluit
from .factories import ZaakFactory


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
            response.data,
            [
                {
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
            response.data,
            {
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
