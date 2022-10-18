# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import json
from io import StringIO
from typing import Dict
from unittest.mock import patch

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
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret
from zds_client import ClientAuth

from openzaak.notifications.tests import mock_notification_send, mock_nrc_oas_get


class MockTTY:
    """
    A fake stdin object that pretends to be a TTY to be used in conjunction
    with mock_inputs.
    """

    def isatty(self):
        return True


def mock_input(prompts: Dict[str, str]):
    def mocked_input(prompt: str) -> str:
        answer = prompts.get(prompt, "")
        return answer

    return patch("builtins.input", side_effect=mocked_input)


@override_settings(NOTIFICATIONS_DISABLED=False)
class SetupConfigurationTests(APITestCase):
    def setUp(self):
        super().setUp()

        self.addCleanup(Site.objects.clear_cache)

    @requests_mock.Mocker()
    def test_non_interactive_without_selftest(self, m):
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "setup_configuration",
            "--no-input",
            ["-v", "0"],
            ["-o", "ACME"],
            ["-d", "open-zaak.example.com"],
            "--create-notifications-api-app",
            ["--notifications-api-app-client-id", "notifications-acme"],
            ["--notifications-api-app-secret", "insecure-oz-secret"],
            ["--notifications-api-root", "https://notifs.example.com"],
            ["--notifications-api-client-id", "oz-acme"],
            ["--notifications-api-secret", "insecure-nrc-secret"],
            "--no-selftest",
            "--no-color",
            stdout=stdout,
            stderr=stderr,
        )

        # minimal output expected
        with self.subTest("Command output"):
            command_output = stdout.getvalue().splitlines()
            expected_output = [
                "Site (domain) configured.",
                "Autorisaties API credentials configured.",
                "Notifications API configured.",
            ]
            self.assertEqual(command_output, expected_output)

        with self.subTest("Site configured correctly"):
            site = Site.objects.get_current()
            self.assertEqual(site.domain, "open-zaak.example.com")
            self.assertEqual(site.name, "Open Zaak ACME")

        with self.subTest("Notifications API can query Autorisaties API"):
            auth = ClientAuth("notifications-acme", "insecure-oz-secret")

            response = self.client.get(
                reverse("applicatie-list", kwargs={"version": 1}),
                HTTP_AUTHORIZATION=auth.credentials()["Authorization"],
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("Notifications API client configured correctly"):
            mock_nrc_oas_get(m)
            mock_notification_send(m)
            notificaties_client = NotificationsConfig.get_client()
            self.assertIsNotNone(notificaties_client)

            response_data = notificaties_client.create(
                "notificaties", data={"foo": "bar"}
            )

            self.assertEqual(response_data, {"dummy": "json"})
            create_call = m.last_request
            self.assertEqual(create_call.url, "https://notifs.example.com/notificaties")
            self.assertIn("Authorization", create_call.headers)
            header_jwt = create_call.headers["Authorization"].split(" ")[1]
            decoded_jwt = decode(header_jwt, options={"verify_signature": False})
            self.assertEqual(decoded_jwt["client_id"], "oz-acme")

    def test_non_interactive_no_args(self):
        """
        Test that non-interactive no-arg commands are no-op.
        """
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "setup_configuration",
            "--no-selftest",
            "--no-color",
            stdout=stdout,
            stderr=stderr,
            interactive=False,
        )

        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Instance configuration completed.", stdout.getvalue())

    def test_domain_input_normalization(self):
        stdout, stderr = StringIO(), StringIO()
        inputs = (
            ("http://localhost:8000", "localhost:8000"),
            ("http://localhost:8000/some-path", "localhost:8000/some-path"),
            ("example.com", "example.com"),
            ("example.com/some-path/", "example.com/some-path/"),
            ("localhost:8000", "localhost:8000"),
            ("localhost:8000/some-path/", "localhost:8000/some-path/"),
        )

        for input_domain, expected_output in inputs:
            with self.subTest(input=input_domain):
                call_command(
                    "setup_configuration",
                    "--no-input",
                    ["-v", "0"],
                    ["-o", "ACME"],
                    ["-d", input_domain],
                    "--no-create-notifications-api-app",
                    "--no-selftest",
                    "--no-color",
                    interactive=False,
                    stdout=stdout,
                    stderr=stderr,
                )
                site = Site.objects.get_current()
                self.assertEqual(site.domain, expected_output)

    def test_invalid_notifications_api_root(self):
        stdout, stderr = StringIO(), StringIO()

        inputs = (
            ("notifs.example.com", "URL must include scheme (like 'https://')"),
            (
                "https:///blah",
                "URL must include host information (like 'notifications.example.com')",
            ),
        )

        for input_host, error_msg in inputs:
            with self.subTest(input=input_host):
                expected_error = (
                    f"Error: argument --notifications-api-root: {error_msg}"
                )
                with self.assertRaisesMessage(CommandError, expected_error):
                    call_command(
                        "setup_configuration",
                        "--no-input",
                        ["--notifications-api-root", input_host],
                        ["-v", "0"],
                        ["-o", "ACME"],
                        "--no-create-notifications-api-app",
                        "--no-selftest",
                        "--no-color",
                        interactive=False,
                        stdout=stdout,
                        stderr=stderr,
                    )

    def test_interactive_without_tty(self):
        stdout, stderr = StringIO(), StringIO()

        class NoTTY:
            def isatty(self):
                return False

        with self.assertRaises(CommandError):
            call_command(
                "setup_configuration",
                interactive=True,
                stdin=NoTTY(),
                stdout=stdout,
                stderr=stderr,
            )

    @requests_mock.Mocker()
    def test_interactive_command(self, m):
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "My Org",
            "Domain (leave blank to use 'example.com'): ": "localhost:9000",
            "Create Notifications API application? [Y/n]: ": "",
            "Notifications app: CLIENT ID (leave blank to generate one): ": "",
            "Notifications app: SECRET (leave blank to generate one): ": "",
            "Notifications API root (leave blank to use '(unset)'): ": "https://notifs.example.com",
            "Test domain configuration by retrieving the homepage? [Y/n]: ": "n",
            "Test Autorisaties API credentials? [Y/n]: ": "n",
            "Test Notifications API access? [Y/n]: ": "N",
            "Send a test notification? [Y/n]: ": "no",
        }

        with mock_input(PROMPTS):
            call_command(
                "setup_configuration",
                interactive=True,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        with self.subTest("Site configured correctly"):
            site = Site.objects.get_current()
            self.assertEqual(site.domain, "localhost:9000")
            self.assertEqual(site.name, "Open Zaak My Org")

        with self.subTest("Notifications API can query Autorisaties API"):
            # get generated client credentials
            app = Applicatie.objects.get(label="Notificaties API My Org")
            client_id = app.client_ids[0]
            secret = JWTSecret.objects.get(identifier=client_id).secret
            auth = ClientAuth(client_id, secret)

            response = self.client.get(
                reverse("applicatie-list", kwargs={"version": 1}),
                HTTP_AUTHORIZATION=auth.credentials()["Authorization"],
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("Notifications API client configured correctly"):
            mock_nrc_oas_get(m)
            mock_notification_send(m)
            notificaties_client = NotificationsConfig.get_client()
            self.assertIsNotNone(notificaties_client)

            response_data = notificaties_client.create(
                "notificaties", data={"foo": "bar"}
            )

            self.assertEqual(response_data, {"dummy": "json"})
            create_call = m.last_request
            self.assertEqual(create_call.url, "https://notifs.example.com/notificaties")
            self.assertIn("Authorization", create_call.headers)
            header_jwt = create_call.headers["Authorization"].split(" ")[1]
            decoded_jwt = decode(header_jwt, options={"verify_signature": False})
            self.assertEqual(decoded_jwt["client_id"], "open-zaak-my-org")

    def test_interactive_command_json_output(self):
        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "My Org",
            "Domain (leave blank to use 'example.com'): ": "localhost:9000",
            "Create Notifications API application? [Y/n]: ": "",
            "Notifications app: CLIENT ID (leave blank to generate one): ": "",
            "Notifications app: SECRET (leave blank to generate one): ": "",
            "Notifications API root (leave blank to use '(unset)'): ": "https://notifs.example.com",
            "Test domain configuration by retrieving the homepage? [Y/n]: ": "n",
            "Test Autorisaties API credentials? [Y/n]: ": "n",
            "Test Notifications API access? [Y/n]: ": "N",
            "Send a test notification? [Y/n]: ": "no",
        }

        for disabled in (True, False):
            stdout, stderr = StringIO(), StringIO()

            with self.subTest(NOTIFICATIONS_DISABLED=disabled), override_settings(
                NOTIFICATIONS_DISABLED=disabled
            ), mock_input(PROMPTS):
                call_command(
                    "setup_configuration",
                    "--json",
                    interactive=True,
                    stdin=MockTTY(),
                    stdout=stdout,
                    stderr=stderr,
                )

            try:
                json.loads(stdout.getvalue())
            except Exception:
                self.fail("Output cannot be parsed as JSON")

    def test_verbose_output_only_missing_info(self):
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "",
            "Send a test notification? [Y/n]: ": "no",
        }

        with mock_input(PROMPTS):
            call_command(
                "setup_configuration",
                "--no-color",
                verbosity=2,
                domain="localhost:8000",
                notifications_provision_ac_client=False,
                notifications_api_root="https://notifs.example.com",
                do_self_test=False,
                interactive=True,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        command_output = stdout.getvalue()
        expected_text = (
            "The organization name is used in labels and Client ID suffixes. "
            "We recommend setting a proper value."
        )
        self.assertIn(expected_text, command_output)

    def test_interactive_no_promts_if_all_options_given(self):
        stdout, stderr = StringIO(), StringIO()

        with mock_input({}) as m:
            call_command(
                "setup_configuration",
                "--no-color",
                verbosity=2,
                organization="ACME",
                domain="localhost:8000",
                notifications_provision_ac_client=False,
                notifications_api_root="https://notifs.example.com",
                notifications_api_client_id="foo",
                notifications_api_secret="bar",
                do_self_test=False,
                interactive=True,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        m.assert_not_called()

    def test_interactive_skip_ac_client(self):
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "My Org",
            "Domain (leave blank to use 'example.com'): ": "localhost:9000",
            "Create Notifications API application? [Y/n]: ": "n",
            "Notifications API root (leave blank to use '(unset)'): ": "https://notifs.example.com",
            "Test domain configuration by retrieving the homepage? [Y/n]: ": "n",
            "Test Autorisaties API credentials? [Y/n]: ": "n",
            "Test Notifications API access? [Y/n]: ": "N",
            "Send a test notification? [Y/n]: ": "no",
        }

        with mock_input(PROMPTS):
            call_command(
                "setup_configuration",
                interactive=True,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        with self.subTest("No Autorisaties API client created"):
            self.assertFalse(Applicatie.objects.exists())
            self.assertFalse(JWTSecret.objects.exists())

    @override_settings(NOTIFICATIONS_DISABLED=True)
    def test_no_configure_notificaties_api_when_disabled(self):
        stdout, stderr = StringIO(), StringIO()

        call_command(
            "setup_configuration",
            "--no-color",
            verbosity=2,
            organization="ACME",
            domain="localhost:8000",
            notifications_provision_ac_client=False,
            do_self_test=False,
            interactive=True,
            stdin=MockTTY(),
            stdout=stdout,
            stderr=stderr,
        )

        config = NotificationsConfig.get_solo()
        self.assertIsNone(config.notifications_api_service)

    def test_no_prompt_self_test_in_non_interactive_mode(self):
        stdout, stderr = StringIO(), StringIO()

        with mock_input({}) as mocked_input:
            call_command(
                "setup_configuration",
                "--no-color",
                organization="ACME",
                domain="localhost:8000",
                notifications_provision_ac_client=False,
                interactive=False,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        mocked_input.assert_not_called()

    @requests_mock.Mocker()
    def test_send_test_notification(self, m):
        stdout, stderr = StringIO(), StringIO()

        # configure instance without check to set up test data
        call_command(
            "setup_configuration",
            ["-v", "0"],
            ["-o", "ACME"],
            ["-d", "open-zaak.example.com"],
            "--no-create-notifications-api-app",
            ["--notifications-api-root", "https://notifs.example.com"],
            "--no-send-test-notification",
            "--no-selftest",
            stdout=stdout,
            stderr=stderr,
            interactive=False,
        )

        self.assertEqual(len(m.request_history), 0)

        # set up mocks now the instance is configured
        mock_nrc_oas_get(m)
        mock_notification_send(m)
        m.get(
            "https://notifs.example.com/kanaal?naam=test", json=[{"naam": "test"}],
        )

        call_command(
            "setup_configuration",
            ["-v", "0"],
            ["--notifications-api-root", "https://notifs.example.com"],
            "--send-test-notification",
            stdout=stdout,
            stderr=stderr,
            interactive=False,
        )

        send_notification = m.last_request
        self.assertEqual(send_notification.method, "POST")
        self.assertEqual(
            send_notification.url, "https://notifs.example.com/notificaties"
        )

    @override_settings(NOTIFICATIONS_DISABLED=False)
    def test_no_generate_credentials_from_prompt(self):
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Notifications app: CLIENT ID (leave blank to generate one): ": "oz-client",
            "Notifications app: SECRET (leave blank to generate one): ": "oz-secret",
            "Notifications API: CLIENT ID (leave blank to generate one): ": "notifs-client",
            "Notifications API: SECRET (leave blank to generate one): ": "notifs-secret",
        }

        with mock_input(PROMPTS):
            call_command(
                "setup_configuration",
                "--json",
                "--no-color",
                interactive=True,
                organization="ACME",
                domain="testserver",
                notifications_provision_ac_client=True,
                notifications_api_root="https://notifs.example.com",
                do_self_test=False,
                send_test_notification=False,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        # assert that the credentials are echoed back in json format (for machine reading)
        command_output = stdout.getvalue()
        output = json.loads(command_output)

        self.assertEqual(
            output["autorisatiesAPIClientCredentials"]["data"],
            {"client_id": "oz-client", "secret": "oz-secret",},
        )
        self.assertEqual(
            output["notificationsAPIConfiguration"]["data"],
            {"client_id": "notifs-client", "secret": "notifs-secret",},
        )

    @requests_mock.Mocker()
    @override_settings(NOTIFICATIONS_DISABLED=True)
    def test_self_test_succeeds(self, m):
        m.get("http://localhost:9000/", status_code=200)
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "My Org",
            "Domain (leave blank to use 'example.com'): ": "localhost:9000",
            "Create Notifications API application? [Y/n]: ": "n",
            "Test domain configuration by retrieving the homepage? [Y/n]: ": "Yes",
            "Test Autorisaties API credentials? [Y/n]: ": "n",
            "Test Notifications API access? [Y/n]: ": "N",
            "Send a test notification? [Y/n]: ": "no",
        }

        with mock_input(PROMPTS):
            call_command(
                "setup_configuration",
                interactive=True,
                stdin=MockTTY(),
                stdout=stdout,
                stderr=stderr,
            )

        self.assertEqual(m.last_request.method, "GET")
        self.assertEqual(m.last_request.url, "http://localhost:9000/")

    @requests_mock.Mocker()
    @override_settings(NOTIFICATIONS_DISABLED=True)
    def test_self_test_fails(self, m):
        m.get("http://localhost:9000/", exc=requests.ConnectionError)
        stdout, stderr = StringIO(), StringIO()

        PROMPTS = {
            "Organization (leave blank to use 'ACME'): ": "My Org",
            "Domain (leave blank to use 'example.com'): ": "localhost:9000",
            "Create Notifications API application? [Y/n]: ": "n",
            "Test domain configuration by retrieving the homepage? [Y/n]: ": "Yes",
            "Test Autorisaties API credentials? [Y/n]: ": "n",
            "Test Notifications API access? [Y/n]: ": "N",
            "Send a test notification? [Y/n]: ": "no",
        }

        with self.assertRaisesMessage(
            CommandError, "Could not access home page at 'http://localhost:9000/'"
        ):
            with mock_input(PROMPTS):
                call_command(
                    "setup_configuration",
                    interactive=True,
                    stdin=MockTTY(),
                    stdout=stdout,
                    stderr=stderr,
                )
