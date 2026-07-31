# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import PositiveInt

from openzaak.components.autorisaties.models import Applicatie
from openzaak.selectielijst.models import ReferentieLijstConfig


class SelectielijstAPIConfig(ConfigurationModel):
    allowed_years: list[PositiveInt] = DjangoModelRef(
        ReferentieLijstConfig, "allowed_years", examples=[[2017, 2020]]
    )

    selectielijst_api_service_identifier: str = DjangoModelRef(
        ReferentieLijstConfig,
        "service",
        examples=["selectielijst-api"],
        description="Identifier of the Selectielijst API service",
    )

    class Meta:
        django_model_refs = {
            ReferentieLijstConfig: [
                "default_year",
            ],
        }


class SingleApplicatieConfigurationModel(ConfigurationModel):
    """
    Copied over from commonground-api-common because of new applicatie model
    """

    uuid: str
    client_ids: list[str]
    label: str
    heeft_alle_autorisaties: bool

    class Meta:
        django_model_refs = {
            Applicatie: ["uuid", "client_ids", "label", "heeft_alle_autorisaties"]
        }
        extra_kwargs = {
            "client_ids": {"examples": [["open-notificaties-prod"]]},
            "label": {"examples": ["Open Notificaties (productie)"]},
        }


class ApplicatieConfigurationModel(ConfigurationModel):
    items: list[SingleApplicatieConfigurationModel]
