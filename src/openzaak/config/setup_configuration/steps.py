# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

# from django.conf import settings

from django_setup_configuration.configuration import BaseConfigurationStep
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.config.setup_configuration.models import (
    DemoConfig,
    SelectielijstAPIConfig,
)
from openzaak.selectielijst.models import ReferentieLijstConfig


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


class SelectielijstAPIConfigurationStep(BaseConfigurationStep[SelectielijstAPIConfig]):
    """
    Configure the Open Zaak client to request Selectielijst API

    1. Create service for Selectielijst API
    2. Set up configuration for Selectielijst API client

    Normal mode doesn't change the allowed and default years
    If they are changed, run this command with 'overwrite' flag
    """

    verbose_name = "Selectielijst API Configuration"
    enable_setting = "openzaak_selectielijst_config_enable"
    namespace = "openzaak_selectielijst_config"
    config_model = SelectielijstAPIConfig

    def execute(self, model: SelectielijstAPIConfig) -> None:

        # 1. Set up a service for the Selectielijst API so Open Zaak can request it
        service, created = Service.objects.update_or_create(
            api_root=model.api_root,
            defaults={
                "label": "Selectielijst API",
                "slug": model.api_root,
                "api_type": APITypes.orc,
                "oas": model.oas,
                "auth_type": AuthTypes.no_auth,
            },
        )
        if not created:
            service.oas = model.SELECTIELIJST_API_OAS
            service.save(update_fields=["oas"])

        # 2. Set up configuration
        config = ReferentieLijstConfig.get_solo()
        if (
            getattr(getattr(config, "service", None), "api_root", None)
            != model.api_root
        ):
            config.service = service
            config.allowed_years = model.allowed_years
            config.default_year = model.default_year
            config.save(update_fields=["service", "allowed_years", "default_year"])
