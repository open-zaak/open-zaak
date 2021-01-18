# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Test the correct invocations for registering notification channels.
"""
from django.core.management import call_command
from django.test import TestCase

import jwt
import requests_mock
from vng_api_common.notifications.models import NotificationsConfig
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.tests.utils import mock_service_oas_get


class RegisterKanaalTests(TestCase):
    def test_correct_credentials_used(self):
        svc, _ = Service.objects.update_or_create(
            api_root="https://open-notificaties.local/api/v1/",
            defaults=dict(
                label="NRC",
                api_type=APITypes.nrc,
                client_id="some-client-id",
                secret="some-secret",
                auth_type=AuthTypes.zgw,
            ),
        )
        config = NotificationsConfig.get_solo()
        config.api_root = svc.api_root
        config.save()

        with requests_mock.Mocker() as m:
            mock_service_oas_get(m, "nrc", url=svc.api_root)
            m.get("https://open-notificaties.local/api/v1/kanaal?naam=zaken", json=[])
            m.post("https://open-notificaties.local/api/v1/kanaal", status_code=201)

            call_command("register_kanaal", kanaal="zaken")

            # check for auth in the calls
            for request in m.request_history[1:]:
                with self.subTest(method=request.method, url=request.url):
                    self.assertIn("Authorization", request.headers)
                    token = request.headers["Authorization"].split(" ")[1]
                    try:
                        jwt.decode(token, key="some-secret", algorithms=["HS256"])
                    except Exception as exc:
                        self.fail("Not a vaid JWT in Authorization header: %s" % exc)
