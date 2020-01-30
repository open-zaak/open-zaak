from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import PermissionDenied


class ZaakClosed(PermissionDenied):
    default_detail = _("You are not allowed to modify closed zaak data.")
