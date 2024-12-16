from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import PositiveInt
from vng_api_common.models import JWTSecret
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig


class DemoConfig(ConfigurationModel):

    demo_client_id = DjangoModelRef(JWTSecret, "identifier")
    demo_secret = DjangoModelRef(JWTSecret, "secret")


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
