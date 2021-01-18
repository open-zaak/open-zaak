# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test that the remote loader makes authenticated calls.
"""
from django.test import TestCase, override_settings

import jwt
import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from ..factories import BesluitFactory
from ..utils import get_besluittype_response


@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitTests(TestCase):
    def test_remote_besluittype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        Service.objects.create(
            api_root="https://externe.catalogus.nl/api/v1/",
            api_type=APITypes.ztc,
            auth_type=AuthTypes.zgw,
            label="external ZTC",
            client_id="client-id",
            secret="secret",
        )
        besluit = BesluitFactory.build(besluittype=besluittype)

        with requests_mock.Mocker() as m:
            m.get(besluittype, json=get_besluittype_response(catalogus, besluittype))
            besluit.besluittype

        request = m.last_request
        self.assertEqual(request.url, besluittype)
        self.assertEqual(request.method, "GET")
        self.assertIn("Authorization", request.headers)

        # Bearer <token>
        bearer, token = request.headers["Authorization"].split(" ")
        self.assertEqual(bearer, "Bearer")

        payload = jwt.decode(token, "secret", algorithms="HS256")
        self.assertEqual(payload["client_id"], "client-id")
