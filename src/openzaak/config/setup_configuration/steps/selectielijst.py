# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from django_setup_configuration.configuration import BaseConfigurationStep
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.config.setup_configuration.models import SelectielijstAPIConfig
from openzaak.selectielijst.models import ReferentieLijstConfig


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
