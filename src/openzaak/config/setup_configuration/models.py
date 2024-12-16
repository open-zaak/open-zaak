from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from vng_api_common.models import JWTSecret


class DemoConfig(ConfigurationModel):

    demo_client_id = DjangoModelRef(JWTSecret, "identifier")
    demo_secret = DjangoModelRef(JWTSecret, "secret")
