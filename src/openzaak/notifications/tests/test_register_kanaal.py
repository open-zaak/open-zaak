# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Test the correct invocations for registering notification channels.
"""
from io import StringIO
from unittest.mock import MagicMock, call, patch

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase, override_settings

import jwt
import requests_mock
from notifications_api_common.kanalen import KANAAL_REGISTRY, Kanaal

from openzaak.components.zaken.models import Zaak

from . import mock_nrc_oas_get
from .mixins import NotificationsConfigMixin


@override_settings(IS_HTTPS=True)
class RegisterKanaalTests(NotificationsConfigMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "example.com"
        site.save()

        kanaal = Kanaal(label="dummy-kanaal", main_resource=Zaak)
        cls.addClassCleanup(lambda: KANAAL_REGISTRY.remove(kanaal))

        cls._configure_notifications(api_root="https://open-notificaties.local/api/v1/")

    def test_correct_credentials_used(self):
        stdout = StringIO()

        with requests_mock.Mocker() as m:
            mock_nrc_oas_get(m)
            m.get("https://open-notificaties.local/api/v1/kanaal?naam=zaken", json=[])
            m.post("https://open-notificaties.local/api/v1/kanaal", status_code=201)

            call_command("register_kanalen", kanalen=["zaken"], stdout=stdout)

            # check for auth in the calls
            for request in m.request_history[1:]:
                with self.subTest(method=request.method, url=request.url):
                    self.assertIn("Authorization", request.headers)
                    token = request.headers["Authorization"].split(" ")[1]
                    try:
                        jwt.decode(token, key="some-secret", algorithms=["HS256"])
                    except Exception as exc:
                        self.fail("Not a vaid JWT in Authorization header: %s" % exc)

    @patch("notifications_api_common.models.NotificationsConfig.get_client")
    def test_kanaal_create_with_name(self, mock_get_client):
        """
        Test is request to create kanaal is send with specified kanaal name
        """
        client = mock_get_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = []  # Mocking the response data for json()
        client.get.return_value = mock_response

        stdout = StringIO()
        call_command(
            "register_kanalen",
            kanalen=["dummy-kanaal"],
            stdout=stdout,
        )

        client.post.assert_called_once_with(
            "kanaal",
            json={
                "naam": "dummy-kanaal",
                "documentatieLink": "https://example.com/ref/kanalen/#dummy-kanaal",
                "filters": [],
            },
        )

    @patch("notifications_api_common.models.NotificationsConfig.get_client")
    def test_kanaal_create_without_name(self, mock_get_client):
        """
        Test is request to create kanaal is send for all registered kanalen
        """
        client = mock_get_client.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = []
        client.get.return_value = mock_response
        client.post.return_value = mock_response

        stdout = StringIO()
        call_command(
            "register_kanalen",
            stdout=stdout,
        )

        client.post.assert_has_calls(
            [
                call(
                    "kanaal",
                    json={
                        "naam": "autorisaties",
                        "documentatieLink": "https://example.com/ref/kanalen/#autorisaties",
                        "filters": [],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "besluiten",
                        "documentatieLink": "https://example.com/ref/kanalen/#besluiten",
                        "filters": [
                            "verantwoordelijke_organisatie",
                            "besluittype",
                            "besluittype.catalogus",
                        ],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "besluittypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#besluittypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "documenten",
                        "documentatieLink": "https://example.com/ref/kanalen/#documenten",
                        "filters": [
                            "bronorganisatie",
                            "informatieobjecttype",
                            "vertrouwelijkheidaanduiding",
                            "informatieobjecttype.catalogus",
                        ],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "dummy-kanaal",
                        "documentatieLink": "https://example.com/ref/kanalen/#dummy-kanaal",
                        "filters": [],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "informatieobjecttypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#informatieobjecttypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "zaaktypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#zaaktypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    json={
                        "naam": "zaken",
                        "documentatieLink": "https://example.com/ref/kanalen/#zaken",
                        "filters": [
                            "bronorganisatie",
                            "zaaktype",
                            "zaaktype.catalogus",
                            "vertrouwelijkheidaanduiding",
                        ],
                    },
                ),
            ]
        )
