from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class NotificatiesConfig(AppConfig):
    name = "openzaak.notificaties"
    label = "openzaak_notificaties"
    verbose_name = _("Notificaties")
