# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import PermissionDenied


class ZaakClosed(PermissionDenied):
    default_detail = _("You are not allowed to modify closed zaak data.")
