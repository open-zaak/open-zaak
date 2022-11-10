# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.test import TestCase

import requests
import requests_mock
from notifications_api_common.models import NotificationsConfig
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from zgw_consumers.constants import AuthTypes
from zgw_consumers.models import Service

from openzaak.notifications.tests import mock_nrc_oas_get
from openzaak.tests.utils.auth import JWTAuthMixin

from ...bootstrap.exceptions import SelfTestFailure
from ...bootstrap.notifications import NotificationsAPIConfiguration


class NotificationsAPIConfigurationTests(TestCase):
    @patch(
        "openzaak.config.bootstrap.notifications.generate_jwt_secret",
        return_value="not-so-random",
    )
    def test_create_missing_configuration(self, mock_generate):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="",
            secret="",
        )

        output = configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertIsNotNone(service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "open-zaak-acme")
        self.assertEqual(service.secret, "not-so-random")

        self.assertEqual(output[0].id, "notificationsAPIConfiguration")
        self.assertEqual(
            output[0].data, {"client_id": "open-zaak-acme", "secret": "not-so-random",}
        )

    def test_create_missing_configuration_explicit_credentials(self):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1/",
            client_id="a-client-id",
            secret="a-secret",
        )

        output = configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertIsNotNone(service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "a-secret")

        self.assertEqual(output[0].id, "notificationsAPIConfiguration")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "a-secret",}
        )

    def test_update_existing_configuration(self):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="a-client-id",
            secret="new-secret",
        )
        # set up service to be replaced
        old_service = Service.objects.create(
            api_root="http://old-notifs.example.com/api/v1", api_type="nrc"
        )
        config = NotificationsConfig.get_solo()
        config.notifications_api_service = old_service
        config.save()

        output = configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertIsNotNone(service)
        self.assertNotEqual(service, old_service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "new-secret")

        self.assertEqual(output[0].id, "notificationsAPIConfiguration")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "new-secret",}
        )

    def test_update_existing_configuration_no_new_service(self):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="a-client-id",
            secret="new-secret",
        )
        # set up service to be replaced
        old_service = Service.objects.create(
            api_root="https://notifs.example.com/api/v1",
            api_type="nrc",
            auth_type=AuthTypes.zgw,
            client_id="old-client-id",
            secret="old-secret",
        )
        config = NotificationsConfig.get_solo()
        config.notifications_api_service = old_service
        config.save()

        output = configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertEqual(service, old_service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "new-secret")

        self.assertEqual(output[0].id, "notificationsAPIConfiguration")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "new-secret",}
        )

    def test_update_no_changes_without_credentials(self):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="a-client-id",
            secret="a-secret",
        )
        configuration.configure()

        configuration2 = NotificationsAPIConfiguration(
            org_name="",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="",
            secret="",
        )
        output = configuration2.configure()
        self.assertEqual(output[0].id, "notificationsAPIConfiguration")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "a-secret",}
        )

    @requests_mock.Mocker()
    def test_configuration_check_ok(self, m):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="",
            secret="",
        )
        configuration.configure()
        mock_nrc_oas_get(m)
        m.get("https://notifs.example.com/api/v1/kanaal", json=[{"naam": "test"}])

        output = configuration.test_configuration()

        self.assertEqual(output[0].id, "notificationsApiChannels")
        self.assertEqual(output[0].data, {"channels": "test"})

    @requests_mock.Mocker()
    def test_configuration_check_failures(self, m):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=False,
            api_root="https://notifs.example.com/api/v1",
            client_id="",
            secret="",
        )
        configuration.configure()
        mock_nrc_oas_get(m)

        mock_kwargs = (
            {"exc": requests.ConnectTimeout},
            {"exc": requests.ConnectionError},
            {"status_code": 404},
            {"status_code": 403},
            {"status_code": 500},
        )
        for mock_config in mock_kwargs:
            with self.subTest(mock=mock_config):
                m.get("https://notifs.example.com/api/v1/kanaal", **mock_config)

                with self.assertRaises(SelfTestFailure):
                    configuration.test_configuration()


class APIStateTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def assertApplicationHasPermissions(self, client_id: str):
        endpoint = reverse("applicatie-consumer", kwargs={"version": "1"})

        response = self.client.get(endpoint, {"client_id": client_id})

        application = response.json()
        nrc_permissions = next(
            (
                perm
                for perm in application["autorisaties"]
                if perm["component"] == "nrc"
            ),
            None,
        )

        self.assertIsNotNone(
            nrc_permissions, "Notificaties API permissions are missing"
        )
        self.assertTrue(
            {"notificaties.consumeren", "notificaties.publiceren"}.issubset(
                set(nrc_permissions["scopes"])
            )
        )

    def test_correct_permissions(self):
        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=True,
            api_root="https://notifs.example.com/api/v1/",
            client_id="a-client-id",
            secret="a-secret",
        )
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")

    def test_extend_existing_configuration(self):
        app = Applicatie.objects.create(
            client_ids=["a-client-id", "another-client-id"], label="A label",
        )
        Autorisatie.objects.create(
            applicatie=app, component="nrc", scopes=["notificaties.consumeren"]
        )

        configuration = NotificationsAPIConfiguration(
            org_name="ACME",
            uses_autorisaties_api=True,
            api_root="https://notifs.example.com/api/v1/",
            client_id="a-client-id",
            secret="a-secret",
        )
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")
