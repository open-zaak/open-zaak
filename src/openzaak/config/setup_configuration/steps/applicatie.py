# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django_setup_configuration import BaseConfigurationStep

from openzaak.components.autorisaties.models import Applicatie
from openzaak.config.setup_configuration.models import ApplicatieConfigurationModel


class ApplicatieConfigurationStep(BaseConfigurationStep[ApplicatieConfigurationModel]):
    """
    Copied over from commonground-api-common because of new applicatie model

    Configure Applicaties used for authorization.

    .. note:: The values of ``client_ids`` must match the values of the ``identifier`` field(s)
        in the ``vng_api_common_credentials`` namespace. To give proper access to an application,
        you need to load the credentials (``identifier`` and ``secret``)
        **and** the Applicatie (``client_ids``, ``uuid``, ``label`` and permissions)
    """

    verbose_name = "Configuration to create applicaties"
    config_model = ApplicatieConfigurationModel
    namespace = "vng_api_common_applicaties"
    enable_setting = "vng_api_common_applicaties_config_enable"

    def execute(self, model: ApplicatieConfigurationModel):
        for config in model.items:
            Applicatie.objects.update_or_create(
                uuid=config.uuid,
                defaults={
                    "client_ids": config.client_ids,
                    "label": config.label,
                    "heeft_alle_autorisaties": config.heeft_alle_autorisaties,
                },
            )
