# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.models import JWTSecret

from openzaak.tests.utils.auth import JWTAuthMixin

from ...bootstrap.notifications import AuthNotificationStep


@override_settings(
    NOTIF_OPENZAAK_CLIENT_ID="a-client-id", NOTIF_OPENZAAK_SECRET="a-secret",
)
class AutorisatiesAPIClientConfigurationTests(TestCase):
    def test_create_configuration(self):
        configuration = AuthNotificationStep()

        configuration.configure()

        app = Applicatie.objects.get()
        self.assertEqual(app.client_ids, ["a-client-id"])
        jwt_secret = JWTSecret.objects.get(identifier="a-client-id")
        self.assertEqual(jwt_secret.secret, "a-secret")

    def test_update_existing_configuration(self):
        app = Applicatie.objects.create(
            client_ids=["a-client-id", "another-client-id"], label="A label",
        )
        jwt_secret = JWTSecret.objects.create(
            identifier="a-client-id", secret="old-secret"
        )
        configuration = AuthNotificationStep()

        configuration.configure()

        jwt_secret.refresh_from_db()
        self.assertEqual(jwt_secret.secret, "a-secret")
        app.refresh_from_db()
        self.assertEqual(app.label, "A label")

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.notifications.build_absolute_url",
        return_value="http://testserver/applicaties",
    )
    def test_configuration_check_ok(self, m, *mocks):
        configuration = AuthNotificationStep()
        configuration.configure()
        m.get("http://testserver/applicaties", json=[])

        configuration.test_configuration()

        self.assertEqual(m.last_request.url, "http://testserver/applicaties")
        self.assertEqual(m.last_request.method, "GET")

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.notifications.build_absolute_url",
        return_value="http://testserver/applicaties",
    )
    def test_configuration_check_failures(self, m, *mocks):
        configuration = AuthNotificationStep()
        configuration.configure()

        mock_kwargs = (
            {"exc": requests.ConnectTimeout},
            {"exc": requests.ConnectionError},
            {"status_code": 404},
            {"status_code": 403},
            {"status_code": 500},
        )
        for mock_config in mock_kwargs:
            with self.subTest(mock=mock_config):
                m.get("http://testserver/applicaties", **mock_config)

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()


@override_settings(
    NOTIF_OPENZAAK_CLIENT_ID="a-client-id", NOTIF_OPENZAAK_SECRET="a-secret",
)
class APIStateTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def assertApplicationHasPermissions(self, client_id: str):
        endpoint = reverse("applicatie-consumer", kwargs={"version": "1"})

        response = self.client.get(endpoint, {"client_id": client_id})

        application = response.json()
        ac_permissions = next(
            (perm for perm in application["autorisaties"] if perm["component"] == "ac"),
            None,
        )
        nrc_permissions = next(
            (
                perm
                for perm in application["autorisaties"]
                if perm["component"] == "nrc"
            ),
            None,
        )

        self.assertIsNotNone(ac_permissions, "Autorisaties API permissions are missing")
        self.assertIsNotNone(
            nrc_permissions, "Notificaties API permissions are missing"
        )

        self.assertTrue({"autorisaties.lezen"}.issubset(set(ac_permissions["scopes"])))
        self.assertTrue(
            {"notificaties.consumeren", "notificaties.publiceren"}.issubset(
                set(nrc_permissions["scopes"])
            )
        )

    def test_correct_permissions(self):
        configuration = AuthNotificationStep()
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")

    def test_extend_existing_configuration(self):
        app = Applicatie.objects.create(
            client_ids=["a-client-id", "another-client-id"], label="A label",
        )
        Autorisatie.objects.create(applicatie=app, component="ac", scopes=[])
        Autorisatie.objects.create(
            applicatie=app, component="nrc", scopes=["notificaties.consumeren"]
        )

        configuration = AuthNotificationStep()
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")
