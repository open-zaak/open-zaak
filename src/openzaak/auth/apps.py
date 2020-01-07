from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class OZAuthConfig(AppConfig):
    name = "openzaak.auth"
    label = "openzaak_auth"
    verbose_name = _("Authentication configuration")
