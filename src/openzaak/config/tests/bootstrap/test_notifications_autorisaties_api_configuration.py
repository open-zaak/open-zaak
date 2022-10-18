# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from unittest.mock import patch

from django.test import TestCase

import requests
import requests_mock
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.models import JWTSecret

from openzaak.tests.utils.auth import JWTAuthMixin

from ...bootstrap.exceptions import SelfTestFailure
from ...bootstrap.notifications import AutorisatiesAPIClientConfiguration


class AutorisatiesAPIClientConfigurationTests(TestCase):
    @patch(
        "openzaak.config.bootstrap.notifications.generate_jwt_secret",
        return_value="not-so-random",
    )
    def test_create_missing_configuration(self, mock_generate):
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="", secret=""
        )

        output = configuration.configure()

        app = Applicatie.objects.get()
        # client ID generated
        self.assertEqual(len(app.client_ids), 1)
        client_id = app.client_ids[0]
        self.assertTrue(
            JWTSecret.objects.filter(
                identifier=client_id, secret="not-so-random"
            ).exists()
        )

        self.assertEqual(output[0].id, "autorisatiesAPIClientCredentials")
        self.assertEqual(
            output[0].data, {"client_id": client_id, "secret": "not-so-random",}
        )

    def test_create_missing_configuration_explicit_credentials(self):
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="a-client-id", secret="a-secret"
        )

        output = configuration.configure()

        app = Applicatie.objects.get()
        # client ID generated
        self.assertEqual(app.client_ids, ["a-client-id"])
        jwt_secret = JWTSecret.objects.get(identifier="a-client-id")
        self.assertEqual(jwt_secret.secret, "a-secret")
        self.assertEqual(output[0].id, "autorisatiesAPIClientCredentials")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "a-secret",}
        )

    def test_update_existing_configuration(self):
        app = Applicatie.objects.create(
            client_ids=["a-client-id", "another-client-id"], label="A label",
        )
        jwt_secret = JWTSecret.objects.create(
            identifier="a-client-id", secret="old-secret"
        )
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="a-client-id", secret="new-secret"
        )

        output = configuration.configure()

        jwt_secret.refresh_from_db()
        self.assertEqual(jwt_secret.secret, "new-secret")
        app.refresh_from_db()
        self.assertEqual(app.label, "A label")
        self.assertEqual(output[0].id, "autorisatiesAPIClientCredentials")
        self.assertEqual(
            output[0].data, {"client_id": "a-client-id", "secret": "new-secret",}
        )

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.notifications.build_absolute_url",
        return_value="http://testserver/applicaties",
    )
    def test_configuration_check_ok(self, m, *mocks):
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="", secret=""
        )
        configuration.configure()
        m.get("http://testserver/applicaties", json=[])

        output = configuration.test_configuration()

        self.assertEqual(output[0].id, "autorisatiesAPIClientSelfTest")
        self.assertEqual(output[0].data, {"success": True})

    @requests_mock.Mocker()
    @patch(
        "openzaak.config.bootstrap.notifications.build_absolute_url",
        return_value="http://testserver/applicaties",
    )
    def test_configuration_check_failures(self, m, *mocks):
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="", secret=""
        )
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

                with self.assertRaises(SelfTestFailure):
                    configuration.test_configuration()


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
        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="a-client-id", secret="a-secret"
        )
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

        configuration = AutorisatiesAPIClientConfiguration(
            org_name="ACME", client_id="a-client-id", secret="a-secret"
        )
        configuration.configure()

        self.assertApplicationHasPermissions("a-client-id")
