# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
import sys
from contextlib import contextmanager
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.serializers.base import DeserializationError

import yaml
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed
from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.models import Applicatie


@contextmanager
def override_stdin(data):
    original_stdin = sys.stdin
    sys.stdin = data
    try:
        yield
    finally:
        sys.stdin = original_stdin


class AuthorizationConfigurationStep(BaseConfigurationStep):
    """
    Configure the Applicaties and Autorisaties.

    From: https://open-zaak.readthedocs.io/en/stable/manual/api-authorizations.html
    """

    verbose_name = "Authorization configuration"
    required_settings = [
        "AUTHORIZATIONS_CONFIG_FIXTURE_PATH",
    ]
    enable_setting = "AUTHORIZATIONS_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        with open(settings.AUTHORIZATIONS_CONFIG_FIXTURE_PATH) as f:
            data = yaml.safe_load(f.read())
            existing_uuids = set(
                str(uuid) for uuid in Applicatie.objects.values_list("uuid", flat=True)
            )
            applicatie_uuids = {
                row["fields"]["uuid"]
                for row in data
                if row["model"] == "authorizations.applicatie"
            }
            applicaties_configured = applicatie_uuids.issubset(existing_uuids)

            existing_identifiers = set(
                str(uuid)
                for uuid in JWTSecret.objects.values_list("identifier", flat=True)
            )

            identifiers = {
                row["fields"]["identifier"]
                for row in data
                if row["model"] == "vng_api_common.jwtsecret"
            }
            secrets_configured = identifiers.issubset(existing_identifiers)

        return applicaties_configured and secrets_configured

    def configure(self):
        with open(settings.AUTHORIZATIONS_CONFIG_FIXTURE_PATH) as original_file:
            content = original_file.read()

            if settings.AUTHORIZATIONS_CONFIG_DOMAIN_MAPPING_PATH:
                with open(
                    settings.AUTHORIZATIONS_CONFIG_DOMAIN_MAPPING_PATH
                ) as mapping_file:
                    mapping = yaml.safe_load(mapping_file)
                    for entry in mapping:
                        for env, domain in entry.items():
                            if env == settings.ENVIRONMENT:
                                continue

                            content = content.replace(
                                domain, entry[settings.ENVIRONMENT]
                            )

            # Load via stdin to avoid having to write to a temporary file
            with override_stdin(StringIO(content)):
                try:
                    call_command("loaddata", "-", format="yaml")
                except DeserializationError as e:
                    raise ConfigurationRunFailed from e.__cause__

    def test_configuration(self): ...
