# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed
from notifications_api_common.models import NotificationsConfig
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from zgw_consumers.constants import AuthTypes
from zgw_consumers.models import Service

from openzaak.notifications.tests import mock_nrc_oas_get
from openzaak.tests.utils.auth import JWTAuthMixin

from ...bootstrap.notifications import NotificationsAPIConfigurationStep


@override_settings(
    NOTIF_API_ROOT="https://notifs.example.com/api/v1/",
    NOTIF_API_OAS="https://notifs.example.com/api/v1/schema/openapi.yaml",
    OPENZAAK_NOTIF_CLIENT_ID="a-client-id",
    OPENZAAK_NOTIF_SECRET="a-secret",
    SOLO_CACHE=None,
)
class NotificationsAPIConfigurationTests(TestCase):
    def test_create_configuration(self):
        configuration = NotificationsAPIConfigurationStep()

        configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertIsNotNone(service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "a-secret")

    def test_update_existing_configuration(self):
        # set up service to be replaced
        old_service = Service.objects.create(
            api_root="http://old-notifs.example.com/api/v1", api_type="nrc"
        )
        config = NotificationsConfig.get_solo()
        config.notifications_api_service = old_service
        config.save()

        configuration = NotificationsAPIConfigurationStep()
        configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertIsNotNone(service)
        self.assertNotEqual(service, old_service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "a-secret")

    def test_update_existing_configuration_no_new_service(self):
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

        configuration = NotificationsAPIConfigurationStep()
        configuration.configure()

        service = NotificationsConfig.get_solo().notifications_api_service
        self.assertEqual(service, old_service)
        self.assertEqual(service.api_root, "https://notifs.example.com/api/v1/")
        self.assertEqual(service.client_id, "a-client-id")
        self.assertEqual(service.secret, "a-secret")

    @requests_mock.Mocker()
    def test_configuration_check_ok(self, m):
        configuration = NotificationsAPIConfigurationStep()
        configuration.configure()
        mock_nrc_oas_get(m)
        m.get("https://notifs.example.com/api/v1/kanaal", json=[{"naam": "test"}])

        configuration.test_configuration()

        req_get_kanaal = [
            req
            for req in m.request_history
            if req.method == "GET"
            and req.url == "https://notifs.example.com/api/v1/kanaal"
        ]
        self.assertEqual(len(req_get_kanaal), 1)

    @requests_mock.Mocker()
    def test_configuration_check_failures(self, m):
        configuration = NotificationsAPIConfigurationStep()
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

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()

    def test_is_configured(self):
        configuration = NotificationsAPIConfigurationStep()

        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())


@override_settings(
    NOTIF_API_ROOT="https://notifs.example.com/api/v1/",
    NOTIF_API_OAS="https://notifs.example.com/api/v1/schema/openapi.yaml",
    OPENZAAK_NOTIF_CLIENT_ID="a-client-id",
    OPENZAAK_NOTIF_SECRET="a-secret",
)
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
        configuration = NotificationsAPIConfigurationStep()
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")

    def test_extend_existing_configuration(self):
        app = Applicatie.objects.create(
            client_ids=["a-client-id", "another-client-id"],
            label="A label",
        )
        Autorisatie.objects.create(
            applicatie=app, component="nrc", scopes=["notificaties.consumeren"]
        )

        configuration = NotificationsAPIConfigurationStep()
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")
