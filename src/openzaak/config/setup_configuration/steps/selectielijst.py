# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed
from zgw_consumers.models import Service

from openzaak.config.setup_configuration.models import SelectielijstAPIConfig
from openzaak.selectielijst.models import ReferentieLijstConfig


def get_service(slug: str) -> Service:
    """
    Try to find a Service and raise ConfigurationRunFailed with the identifier
    to make debugging easier
    """
    try:
        return Service.objects.get(slug=slug)
    except Service.DoesNotExist as e:
        raise ConfigurationRunFailed(f"{str(e)} (identifier = {slug})")


class SelectielijstAPIConfigurationStep(BaseConfigurationStep[SelectielijstAPIConfig]):
    """
    Configure the Open Zaak client to request Selectielijst API

    This step is dependent on the previous ``ServiceConfigurationStep``
    to load a ``Service`` for this Selectielijst API, which is referred to in this step by
    ``selectielijst_api_service_identifier``.
    """

    verbose_name = "Selectielijst API Configuration"
    enable_setting = "openzaak_selectielijst_config_enable"
    namespace = "openzaak_selectielijst_config"
    config_model = SelectielijstAPIConfig

    def execute(self, model: SelectielijstAPIConfig) -> None:

        service = get_service(model.selectielijst_api_service_identifier)

        config = ReferentieLijstConfig.get_solo()
        config.service = service
        config.allowed_years = model.allowed_years
        config.default_year = model.default_year
        config.save()
