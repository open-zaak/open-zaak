# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.conf import settings
from django.core.management import call_command

import yaml
from django_setup_configuration.configuration import BaseConfigurationStep
from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.models import Applicatie


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
        call_command("loaddata", settings.AUTHORIZATIONS_CONFIG_FIXTURE_PATH)

    def test_configuration(self):
        # TODO test access for each application? seems a bit excessive
        ...
