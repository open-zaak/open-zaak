# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from django_setup_configuration.configuration import BaseConfigurationStep
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from openzaak.config.setup_configuration.models import DemoConfig


class DemoUserStep(BaseConfigurationStep[DemoConfig]):
    """
    Create demo user to request Open Zaak APIs

    **NOTE** For now demo user has all permissions.

    Normal mode doesn't change the secret after its initial creation.
    Run this command with the 'overwrite' flag to change the secret
    """

    verbose_name = "Demo User Configuration"
    config_model = DemoConfig
    namespace = "demo_config"
    enable_setting = "demo_config_enable"

    def execute(self, model: DemoConfig) -> None:

        # store client_id and secret
        jwt_secret, created = JWTSecret.objects.get_or_create(
            identifier=model.demo_client_id,
            defaults={"secret": model.demo_secret},
        )
        if jwt_secret.secret != model.demo_secret:
            jwt_secret.secret = model.demo_secret
            jwt_secret.save(update_fields=["secret"])

        # check for the application
        if not Applicatie.objects.filter(
            client_ids__contains=[model.demo_client_id]
        ).exists():
            Applicatie.objects.create(
                client_ids=[model.demo_client_id],
                label="Demo user",
                heeft_alle_autorisaties=True,
            )
