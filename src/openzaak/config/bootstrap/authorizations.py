# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
import logging
import sys
from contextlib import contextmanager
from io import StringIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.serializers.base import DeserializationError
from django.db import transaction

import yaml
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.models import Applicatie, CatalogusAutorisatie
from openzaak.components.autorisaties.validators import (
    validate_authorizations_have_scopes,
)

logger = logging.getLogger(__name__)

DISALLOWED_SETTINGS = [
    "OPENZAAK_NOTIF_CONFIG_ENABLE",
    "NOTIF_OPENZAAK_CONFIG_ENABLE",
    "DEMO_CONFIG_ENABLE",
]


@contextmanager
def override_stdin(data):
    original_stdin = sys.stdin
    sys.stdin = data
    try:
        yield
    finally:
        sys.stdin = original_stdin


def delete_existing_configuration() -> None:
    logger.info("Removing all existing authorization configuration")

    Applicatie.objects.all().delete()
    Autorisatie.objects.all().delete()
    CatalogusAutorisatie.objects.all().delete()
    JWTSecret.objects.all().delete()


def filter_entries(fixture: list[dict], models: list[str]) -> list[dict]:
    """
    Filter and prepare the fixture for validation
    """
    return [entry["fields"] for entry in fixture if entry["model"] in models]


def validate_fixture(fixture: list[dict]) -> None:
    """
    Validate the fixture using the same validation methods used by the Autorisaties admin
    """
    errors = []
    try:
        data = filter_entries(
            fixture,
            ["autorisaties.catalogusautorisatie", "authorizations.autorisatie"],
        )
        validate_authorizations_have_scopes(data)
    except ValidationError as e:
        errors.append(e.message)

    if errors:
        formatted_errors = "\n".join(f"* {error}" for error in errors)
        raise ConfigurationRunFailed(
            "The following errors occurred while validating the authorization "
            "configuration fixture: \n"
            f"{formatted_errors}"
        )


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

    @transaction.atomic
    def configure(self):
        if settings.AUTHORIZATIONS_CONFIG_DELETE_EXISTING:
            if any(getattr(settings, name) for name in DISALLOWED_SETTINGS):
                setting_names = "\n".join(
                    [f"* `{setting}`" for setting in DISALLOWED_SETTINGS]
                )
                raise ConfigurationRunFailed(
                    "AuthorizationConfigurationStep with AUTHORIZATIONS_CONFIG_DELETE_EXISTING=True "
                    "is mutually exclusive with other steps that configure authorization configuration. "
                    "Please set the following settings to False to resolve this: \n"
                    f"{setting_names}"
                )

            delete_existing_configuration()

        with open(settings.AUTHORIZATIONS_CONFIG_FIXTURE_PATH) as original_file:
            content = original_file.read()

            fixture_data = yaml.safe_load(content)
            validate_fixture(fixture_data)

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
            logger.info(
                "Loading authorization configuration from %s",
                settings.AUTHORIZATIONS_CONFIG_FIXTURE_PATH,
            )
            with override_stdin(StringIO(content)):
                try:
                    call_command("loaddata", "-", format="yaml")
                except DeserializationError as e:
                    raise ConfigurationRunFailed from e.__cause__

            logger.info("Authorization configuration successfully loaded!")

    def test_configuration(self): ...
