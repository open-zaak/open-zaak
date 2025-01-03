# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import PositiveInt
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig


class SelectielijstAPIConfig(ConfigurationModel):

    allowed_years: list[PositiveInt] = DjangoModelRef(
        ReferentieLijstConfig, "allowed_years"
    )

    class Meta:
        django_model_refs = {
            Service: [
                "api_root",
                "oas",
            ],
            ReferentieLijstConfig: [
                "default_year",
            ],
        }
