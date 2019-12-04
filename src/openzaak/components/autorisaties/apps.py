from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = "openzaak.components.autorisaties"
    label = "openzaak_authorizations"
    verbose_name = _("Autorisaties")
