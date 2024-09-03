# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from io import StringIO
from pathlib import Path

from django.contrib.sites.models import Site
from django.core.management import CommandError, call_command
from django.test import override_settings

import requests
import requests_mock
from jwt import decode
from notifications_api_common.models import NotificationsConfig
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.models import JWTSecret
from zds_client import ClientAuth
from zgw_consumers.client import build_client
from zgw_consumers.test import mock_service_oas_get

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.components.catalogi.tests.factories import CatalogusFactory
from openzaak.components.zaken.tests.utils import ZAAK_READ_KWARGS
from openzaak.config.bootstrap.authorizations import AuthorizationConfigurationStep
from openzaak.config.bootstrap.demo import DemoUserStep
from openzaak.config.bootstrap.notifications import (
    AuthNotificationStep,
    NotificationsAPIConfigurationStep,
)
from openzaak.config.bootstrap.selectielijst import SelectielijstAPIConfigurationStep
from openzaak.config.bootstrap.site import SiteConfigurationStep

ZAAKTYPE = "https://acc.openzaak.nl/zaaktypen/1"

AUTH_FIXTURE_PATH = Path(__file__).parents[2] / "config/tests/bootstrap/files/auth.yaml"


@override_settings(
    NOTIFICATIONS_DISABLED=False,
    SITES_CONFIG_ENABLE=True,
    OPENZAAK_DOMAIN="open-zaak.example.com",
    OPENZAAK_ORGANIZATION="ACME",
    NOTIF_API_ROOT="https://notifs.example.com/api/v1/",
    NOTIF_API_OAS="https://notifs.example.com/api/v1/schema/openapi.yaml",
    OPENZAAK_NOTIF_CONFIG_ENABLE=True,
    OPENZAAK_NOTIF_CLIENT_ID="oz-client-id",
    OPENZAAK_NOTIF_SECRET="oz-secret",
    NOTIF_OPENZAAK_CONFIG_ENABLE=True,
    NOTIF_OPENZAAK_CLIENT_ID="notif-client-id",
    NOTIF_OPENZAAK_SECRET="notif-secret",
    OPENZAAK_SELECTIELIJST_CONFIG_ENABLE=True,
    DEMO_CONFIG_ENABLE=True,
    DEMO_CLIENT_ID="demo-client-id",
    DEMO_SECRET="demo-secret",
    AUTHORIZATIONS_CONFIG_ENABLE=True,
    AUTHORIZATIONS_CONFIG_FIXTURE_PATH=AUTH_FIXTURE_PATH,
)
class SetupConfigurationTests(APITestCase):
    def setUp(self):
        super().setUp()

        self.catalogus = CatalogusFactory.create(
            uuid="6de0b166-8e76-477c-901d-123244e4d020"
        )
        self.addCleanup(Site.objects.clear_cache)

    @requests_mock.Mocker()
    def test_setup_configuration_success(self, m):
        stdout = StringIO()
        # mocks
        m.get("http://open-zaak.example.com/", status_code=200)
        m.get("http://open-zaak.example.com/autorisaties/api/v1/applicaties", json=[])
        m.get("http://open-zaak.example.com/zaken/api/v1/zaken", json=[])
        mock_service_oas_get(m, url="https://notifs.example.com/api/v1/", service="nrc")
        m.get("https://notifs.example.com/api/v1/kanaal", json=[{"naam": "test"}])
        m.post("https://notifs.example.com/api/v1/notificaties", status_code=201)

        call_command("setup_configuration", stdout=stdout, no_color=True)

        # minimal output expected
        with self.subTest("Command output"):
            command_output = stdout.getvalue().splitlines()
            expected_output = [
                "Configuration will be set up with following steps: "
                f"[{SiteConfigurationStep()}, {AuthNotificationStep()}, "
                f"{NotificationsAPIConfigurationStep()}, {SelectielijstAPIConfigurationStep()}, "
                f"{DemoUserStep()}, {AuthorizationConfigurationStep()}]",
                f"Configuring {SiteConfigurationStep()}...",
                f"{SiteConfigurationStep()} is successfully configured",
                f"Configuring {AuthNotificationStep()}...",
                f"{AuthNotificationStep()} is successfully configured",
                f"Configuring {NotificationsAPIConfigurationStep()}...",
                f"{NotificationsAPIConfigurationStep()} is successfully configured",
                f"Step {SelectielijstAPIConfigurationStep()} is skipped, because the configuration already exists.",
                f"Configuring {DemoUserStep()}...",
                f"{DemoUserStep()} is successfully configured",
                f"Configuring {AuthorizationConfigurationStep()}...",
                f"{AuthorizationConfigurationStep()} is successfully configured",
                "Instance configuration completed.",
            ]
            self.assertEqual(command_output, expected_output)

        with self.subTest("Site configured correctly"):
            site = Site.objects.get_current()
            self.assertEqual(site.domain, "open-zaak.example.com")
            self.assertEqual(site.name, "Open Zaak ACME")

        with self.subTest("Notifications API can query Autorisaties API"):
            auth = ClientAuth("notif-client-id", "notif-secret")

            response = self.client.get(
                reverse("applicatie-list", kwargs={"version": 1}),
                headers={"authorization": auth.credentials()["Authorization"]},
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("Notifications API client configured correctly"):
            config = NotificationsConfig.get_solo()
            notificaties_client = build_client(config.notifications_api_service)

            self.assertIsNotNone(notificaties_client)

            notificaties_client.request(
                url="notificaties", method="POST", data={"foo": "bar"}
            )

            create_call = m.last_request
            self.assertEqual(
                create_call.url, "https://notifs.example.com/api/v1/notificaties"
            )
            self.assertIn("Authorization", create_call.headers)
            header_jwt = create_call.headers["Authorization"].split(" ")[1]
            decoded_jwt = decode(header_jwt, options={"verify_signature": False})
            self.assertEqual(decoded_jwt["client_id"], "oz-client-id")

        with self.subTest("Demo user configured correctly"):
            auth = ClientAuth("demo-client-id", "demo-secret")

            response = self.client.get(
                reverse("zaak-list", kwargs={"version": 1}),
                **ZAAK_READ_KWARGS,
                HTTP_AUTHORIZATION=auth.credentials()["Authorization"],
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("Authorizations configured correctly"):
            # One for notif-client, one for demo-client, one from auth config
            self.assertEqual(JWTSecret.objects.count(), 4)
            # One for OZ itself, notif-client, one for demo-client, one from auth config
            self.assertEqual(Applicatie.objects.count(), 5)
            # One for OZ itself, notif-client, one for demo-client, one from auth config
            self.assertEqual(Autorisatie.objects.count(), 5)
            # One from auth config
            self.assertEqual(CatalogusAutorisatie.objects.count(), 1)

    @requests_mock.Mocker()
    def test_setup_configuration_selftest_fails(self, m):
        m.get("http://open-zaak.example.com/", exc=requests.ConnectionError)
        m.get("http://open-zaak.example.com/autorisaties/api/v1/applicaties", json=[])
        m.get("http://open-zaak.example.com/zaken/api/v1/zaken", json=[])
        mock_service_oas_get(m, url="https://notifs.example.com/api/v1/", service="nrc")
        m.get("https://notifs.example.com/api/v1/kanaal", json=[{"naam": "test"}])
        m.post("https://notifs.example.com/api/v1/notificaties", status_code=201)

        with self.assertRaisesMessage(
            CommandError,
            "Could not access home page at 'http://open-zaak.example.com/'",
        ):
            call_command("setup_configuration")

    @requests_mock.Mocker()
    def test_setup_configuration_without_selftest(self, m):
        stdout = StringIO()

        call_command("setup_configuration", no_selftest=True, stdout=stdout)
        command_output = stdout.getvalue()

        self.assertEqual(len(m.request_history), 0)
        self.assertTrue("Selftest is skipped" in command_output)
