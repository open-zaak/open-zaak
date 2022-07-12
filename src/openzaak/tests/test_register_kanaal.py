# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Test the correct invocations for registering notification channels.
"""
from django.core.management import call_command
from django.test import TestCase

import jwt
import requests_mock

from openzaak.notifications.tests import mock_nrc_oas_get
from openzaak.notifications.tests.utils import NotificationsConfigMixin


class RegisterKanaalTests(NotificationsConfigMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._configure_notifications(api_root="https://open-notificaties.local/api/v1/")

    def test_correct_credentials_used(self):
        with requests_mock.Mocker() as m:
            mock_nrc_oas_get(m)
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
