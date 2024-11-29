# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.test import override_settings
from django.utils import timezone

import jwt
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.tests import reverse

from openzaak.components.autorisaties.middleware import JWTAuth
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from openzaak.tests.utils import JWTAuthMixin


class JWTExpiredTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2019-01-01T12:00:00")
    def setUp(self):
        super().setUp()

        # zgw-consumers ZGWAuth doesn't allow passing of extra claims (like `nbf`)
        payload = {
            # standard claims
            "iss": self.client_id,
            "iat": int(timezone.now().timestamp()),
            "nbf": int(timezone.now().timestamp()),
            # custom claims
            "client_id": self.client_id,
            "user_id": self.user_id,
            "user_representation": self.user_representation,
        }

        token: str = f"Bearer {jwt.encode(payload, self.secret, algorithm='HS256')}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_jwt_expired(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.get(zaak_url)

        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60, JWT_LEEWAY=3)
    @freeze_time("2019-01-01T13:00:01")
    def test_jwt_leeway_accounts_for_drft(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.get(zaak_url)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60, JWT_LEEWAY=3)
    @freeze_time("2019-01-01T11:59:56")
    def test_iat_greater_than_now(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.get(zaak_url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JWTLeewayTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @freeze_time("2019-01-01T12:00:00")
    def setUp(self):
        super().setUp()

        # zgw-consumers ZGWAuth doesn't allow passing of extra claims (like `nbf`)
        payload = {
            # standard claims
            "iss": self.client_id,
            "iat": int(timezone.now().timestamp()),
            "nbf": int(timezone.now().timestamp()),
            # custom claims
            "client_id": self.client_id,
            "user_id": self.user_id,
            "user_representation": self.user_representation,
        }

        token: str = f"Bearer {jwt.encode(payload, self.secret, algorithm='HS256')}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @freeze_time("2019-01-01T11:59:59")
    def test_jwt_leeway_zero(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.get(zaak_url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-immaturesignatureerror")

    @override_settings(JWT_LEEWAY=3)
    @freeze_time("2019-01-01T11:59:59")
    def test_jwt_leeway_accounts_for_drift(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.get(zaak_url, **ZAAK_WRITE_KWARGS)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JWTRegressionTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_null_user_id(self):
        """
        Assert that ``user_id: null`` claim does not crash Open Zaak.

        Regression test for https://github.com/open-zaak/open-zaak/issues/936
        """
        token = generate_jwt(
            self.client_id,
            self.secret,
            None,
            self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)
        zaak = ZaakFactory.create()
        endpoint = reverse(zaak)
        payload = JWTAuth(token.split(" ")[1]).payload
        assert payload["user_id"] is None

        response = self.client.patch(endpoint, data={}, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
