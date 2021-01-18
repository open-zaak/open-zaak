# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import jwt
from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.utils.tests import JWTAuthMixin

from .utils import get_operation_url


class JWTTests(JWTAuthMixin, APITestCase):
    def test_request_without_eat(self):
        # generate credentials without iat
        payload = {
            # standard claims
            "iss": "testsuite",
            # custom
            "client_id": self.client_id,
            "user_id": self.client_id,
            "user_representation": self.client_id,
        }
        encoded = jwt.encode(payload, self.secret, algorithm="HS256")
        encoded = encoded.decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {encoded}")

        # request any resource
        url = get_operation_url("applicatie_list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(data["code"], "jwt-missing-iat-claim")
