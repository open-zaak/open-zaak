# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import argparse
import json
import logging
import sys
from dataclasses import dataclass
from io import StringIO
from typing import Any, List, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import BaseCommand, CommandError, call_command

from notifications_api_common.models import NotificationsConfig

from openzaak.config.bootstrap.exceptions import SelfTestFailure
from openzaak.config.bootstrap.notifications import (
    AutorisatiesAPIClientConfiguration,
    NotificationsAPIConfiguration,
)
from openzaak.config.bootstrap.site import SiteConfiguration
from openzaak.config.bootstrap.typing import ConfigurationProtocol

logger = logging.getLogger(__name__)


def domain_only_netloc(value: str) -> str:
    if "//" in value:
        parsed = urlparse(value)
        return f"{parsed.netloc}{parsed.path}"
    elif ":" in value:
        host, port = value.split(":", 1)
        return f"{host}:{port}"
    return value


def fq_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme:
        raise argparse.ArgumentTypeError("URL must include scheme (like 'https://')")
    if not parsed.netloc:
        raise argparse.ArgumentTypeError(
            "URL must include host information (like 'notifications.example.com')"
        )
    return value


@dataclass
class ConfigurationStep:
    configuration: ConfigurationProtocol
    info_message: str
    success_message: str
    self_test_prompt: str
    do_self_test: Optional[bool] = None


class Command(BaseCommand):
    help = (
        "Bootstrap the initial Open Zaak configuration. Note that this command is "
        "interacitve - missing input will be prompted for."
    )
    output_transaction = True
    stealth_options = ("stdin",)

    def add_arguments(self, parser):
        # site meta
        parser.add_argument(
            "-o",
            "--org",
            "--organization",
            "--organisation",
            dest="organization",
            default="",
            help=(
                "Name of your organization, e.g. 'ACME'. This is used in labels and "
                "prefixes of configuration aspects (such as client IDs) if provided."
            ),
        )
        parser.add_argument(
            "-d",
            "--domain",
            default=settings.OPENZAAK_DOMAIN,
            type=domain_only_netloc,
            help=(
                "Domain/host of the Open Zaak instance. E.g. 'open-zaak.example.com:4443', "
                "without the 'https://...' prefix. The default value is taken from the "
                "OPENZAAK_DOMAIN setting."
            ),
        )

        # create autorisaties application for notifications API
        parser.add_argument(
            "--create-notifications-api-app",
            dest="notifications_provision_ac_client",
            action=argparse.BooleanOptionalAction,
            help=(
                "Create a client application for the Notifications API in Open Zaak's "
                "autorisaties API. This application is required if your Notifications "
                "API uses the Open Zaak autorisaties API to check permissions of "
                "notification publishers/consumers."
            ),
        )
        parser.add_argument(
            "--notifications-api-app-client-id",
            dest="notifications_ac_client_client_id",
            default="",
            help=(
                "Specify a client ID for the Autorisaties API client. If not specified, "
                "a client ID will be generated. If provided, the existing client will "
                "be looked up by this value, otherwise the label will be derived from "
                "the organization name for lookup."
            ),
        )
        parser.add_argument(
            "--notifications-api-app-secret",
            dest="notifications_ac_client_secret",
            default="",
            help=(
                "Specify a client secret for the Autorisaties API client. If not "
                "specified, a value will be generated."
            ),
        )

        # notifications API - which notifications API to use
        parser.add_argument(
            "--notifications-api-root",
            type=fq_url,
            dest="notifications_api_root",
            help=(
                "Notifications API root URL, including protocol. E.g. "
                "'https://notificaties.example.com/api/v1/'. If provided, the "
                "relevant permissions and service are configured."
            ),
        )
        parser.add_argument(
            "--notifications-api-client-id",
            default="",
            help=(
                "Specify a client ID for the Notifications API. If not specified, a "
                "client ID will be generated. Any existing configuration is looked up "
                "based on this client ID. If not provided, a value is derived from the "
                "organiation name. Requires the --notifications-api option."
            ),
        )
        parser.add_argument(
            "--notifications-api-secret",
            default="",
            help=(
                "Specify a client secret for the Notifications API. If not specified, a "
                "value will be generated. Only when explicitly provided existing "
                "configuration is updated."
            ),
        )
        parser.add_argument(
            "--send-test-notification",
            dest="send_test_notification",
            action=argparse.BooleanOptionalAction,
            help="Send a test notification to the configured Notifications API.",
        )

        # self-test config
        parser.add_argument(
            "--self-test",
            "--selftest",
            dest="do_self_test",
            action=argparse.BooleanOptionalAction,
            help="Skip self-testing the created configuration.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help=(
                "Tells Open Zaak to NOT prompt the user for input of any kind. "
                "Only parameters provided on the command line will be processed."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help=(
                "Outputs results to stdout as JSON. Note that this surpresses any "
                "other informative output."
            ),
        )

    def execute(self, *args, **options):
        self.stdin = options.get("stdin", sys.stdin)  # Used for testing
        return super().execute(*args, **options)

    def handle(self, **options):
        verbosity: int = options["verbosity"]
        self.as_json = options["json"]
        self.verbosity = verbosity

        organization = options["organization"]
        domain = options["domain"]

        # notifications: autorisaties API client
        notifications_provision_ac_client: Optional[bool] = options[
            "notifications_provision_ac_client"
        ]
        notifications_ac_client_client_id = options["notifications_ac_client_client_id"]
        notifications_ac_client_secret = options["notifications_ac_client_secret"]

        # notifications API: Open Zaak is client for this service
        notifications_api_root = options["notifications_api_root"]
        notifications_api_client_id = options["notifications_api_client_id"]
        notifications_api_secret = options["notifications_api_secret"]
        send_test_notification: Optional[bool] = options["send_test_notification"]

        # globally enable/disable self-testing - None if not explicitly provided
        do_self_test: Optional[bool] = options["do_self_test"]

        # Interactively prompt for missing/empty options.
        if options["interactive"]:
            self._check_tty()

            # prompt for organization name
            if not organization:
                self.write_info(
                    "The organization name is used in labels and Client ID suffixes. "
                    "We recommend setting a proper value."
                )
                message = "Organization (leave blank to use 'ACME'): "
                organization = self._get_input_data(message, default="ACME")
                if not self.as_json:
                    self.stdout.write(
                        f"  Continuing with organization name '{organization}'..."
                    )

            if not domain:
                self.write_info(
                    "The domain is used to construct fully qualified (resource) URLs "
                    "to be retrieved by other services if OPENZAAK_DOMAIN is not set."
                )
                current_domain = Site.objects.get_current().domain
                message = f"Domain (leave blank to use '{current_domain}'): "
                domain = self._get_input_data(message, default=current_domain)
                if not self.as_json:
                    self.stdout.write(f"  Continuing with domain '{domain}'...")

            # Autorisaties API configuration for Notifications API
            if notifications_provision_ac_client is None:
                self.write_info(
                    "The Notifications API retrieves permission information from an "
                    "Authorizations API to check whether clients are allowed to "
                    "produce or consume notifications. If your Notifications API uses "
                    "the Authorizations API implemented by Open Zaak (which is "
                    "likely), then the Application record for the Notifications API "
                    "must be configured."
                )
                message = "Create Notifications API application? [Y/n]: "
                notifications_provision_ac_client = self._bool_prompt(
                    message, default="Y"
                )
                if not notifications_provision_ac_client and not self.as_json:
                    self.stdout.write(
                        "  Skipping Notifications API application creation."
                    )

            if (
                notifications_provision_ac_client
                and not notifications_ac_client_client_id
            ):
                message = "Notifications app: CLIENT ID (leave blank to generate one): "
                notifications_ac_client_client_id = self._get_input_data(message)
                if not notifications_ac_client_client_id and not self.as_json:
                    self.stdout.write("  A value will be generated.")

            if notifications_provision_ac_client and not notifications_ac_client_secret:
                message = "Notifications app: SECRET (leave blank to generate one): "
                notifications_ac_client_secret = self._get_input_data(message)
                if not notifications_ac_client_secret and not self.as_json:
                    self.stdout.write("  A value will be generated.")

            if not settings.NOTIFICATIONS_DISABLED:
                # Notifications API configuration
                if not notifications_api_root:
                    self.write_info(
                        "Open Zaak publishes notifications to the Notifications API. "
                        "For this, the connection to the Notifications API must be "
                        "correctly configured.\n\n"
                        "If credentials are generated, make sure to configure those in "
                        "your Notifications API too."
                    )

                    service = NotificationsConfig.get_solo().notifications_api_service
                    current_api_root = service.api_root if service else "(unset)"
                    message = f"Notifications API root (leave blank to use '{current_api_root}'): "
                    notifications_api_root = self._get_input_data(
                        message, default=current_api_root
                    )
                    if not self.as_json:
                        self.stdout.write(
                            f"  Continuing with Notifications API at {notifications_api_root}."
                        )

                if not notifications_api_client_id:
                    message = (
                        "Notifications API: CLIENT ID (leave blank to generate one): "
                    )
                    notifications_api_client_id = self._get_input_data(message)
                    if not notifications_api_client_id and not self.as_json:
                        self.stdout.write("  A value will be generated.")

                if not notifications_api_secret:
                    message = (
                        "Notifications API: SECRET (leave blank to generate one): "
                    )
                    notifications_api_secret = self._get_input_data(message)
                    if not notifications_api_secret and not self.as_json:
                        self.stdout.write("  A value will be generated.")

            elif not self.as_json:
                self.stdout.write(
                    self.style.WARNING(
                        "You currently have notification sending disabled "
                        "(NOTIFICATIONS_DISABLED). Open Zaak will not be publishing "
                        "any notifications."
                    )
                )

        def _prompt_self_test(msg: str) -> bool:
            # explicitly provided via flag -> use that global configuration
            if do_self_test is not None:
                return do_self_test
            # in non-interactive mode, we can't prompt, so assume it's unattended
            # -> no self test by default
            if not options["interactive"]:
                return False
            message = f"{msg} [Y/n]: "
            return self._bool_prompt(message, default="Y")

        steps: List[ConfigurationStep] = []

        if domain:
            steps.append(
                ConfigurationStep(
                    configuration=SiteConfiguration(domain, organization),
                    info_message="Configuring site domain...",
                    success_message="Site (domain) configured.",
                    self_test_prompt="Test domain configuration by retrieving the homepage?",
                )
            )

        if notifications_provision_ac_client:
            steps.append(
                ConfigurationStep(
                    configuration=AutorisatiesAPIClientConfiguration(
                        org_name=organization,
                        client_id=notifications_ac_client_client_id,
                        secret=notifications_ac_client_secret,
                    ),
                    info_message="Configuring Autorisaties API credentials...",
                    success_message="Autorisaties API credentials configured.",
                    self_test_prompt="Test Autorisaties API credentials?",
                )
            )

        if notifications_api_root:
            steps.append(
                ConfigurationStep(
                    configuration=NotificationsAPIConfiguration(
                        org_name=organization,
                        uses_autorisaties_api=bool(notifications_provision_ac_client),
                        api_root=notifications_api_root,
                        client_id=notifications_api_client_id,
                        secret=notifications_api_secret,
                    ),
                    info_message="Configuring Notifications API...",
                    success_message="Notifications API configured.",
                    self_test_prompt="Test Notifications API access?",
                )
            )

        # run all the configuration and collect output
        all_output = []
        for step in steps:
            self.report_step(step.info_message)
            all_output += step.configuration.configure()
            self.write_success(step.success_message)

        try:
            # now prompt for (and run) step self-test
            for step in steps:
                run_self_test = _prompt_self_test(step.self_test_prompt)
                if not run_self_test:
                    continue
                all_output += step.configuration.test_configuration()

        except SelfTestFailure as failure:
            error_message = failure.args[0]
            raise CommandError(error_message) from failure

        if notifications_api_root:
            if send_test_notification is None:
                send_test_notification = _prompt_self_test("Send a test notification?")

            if send_test_notification:
                stdout = self.stdout if not self.as_json else StringIO()
                call_command(
                    "send_test_notification", stdout=stdout, stderr=self.stderr
                )

        if verbosity >= 1:

            if not self.as_json:
                self.stdout.write(self.style.MIGRATE_LABEL("\nResults summary"))

                for output in all_output:
                    self.stdout.write("\n")
                    self.stdout.write(str(output))

                self.stdout.write(
                    self.style.SUCCESS("\nInstance configuration completed.")
                )

            else:
                json_output = {}
                for output in all_output:
                    json_output.update(output.as_json())
                serialized = json.dumps(json_output)
                self.stdout.write(serialized)

    def _get_input_data(
        self, message: str, default: Optional[Any] = None, normalize=lambda x: x
    ) -> Any:
        value: str = input(message).strip()
        if default and value == "":
            value = default
        return normalize(value)

    def _bool_prompt(self, message: str, default: str = "N") -> bool:
        response: str = self._get_input_data(
            message, default=default, normalize=lambda x: x.lower()
        )
        return response in ("y", "yes", "yeah")

    def _check_tty(self):
        if hasattr(self.stdin, "isatty") and not self.stdin.isatty():
            raise CommandError(
                "Cannot prompt for input when not running in a TTY. Either use the "
                "--noinput flag or run this command in a TTY."
            )

    def write_info(self, msg: str):
        if self.verbosity <= 1 or self.as_json:
            return
        self.stdout.write(self.style.HTTP_INFO(msg))

    def write_success(self, msg: str):
        if self.verbosity >= 1 or self.as_json:
            return
        self.stdout.write(self.style.SUCCESS(msg))

    def report_step(self, msg: str):
        if self.verbosity <= 1 or self.as_json:
            return
        self.stdout.write(self.style.MIGRATE_HEADING(msg))
