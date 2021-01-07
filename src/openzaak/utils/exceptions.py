# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import APIException


class DetermineProcessEndDateException(Exception):
    pass


class CMISAdapterException(APIException):
    status_code = 400
    default_code = _("CMIS-adapter error")
    default_detail = _("An error occurred in the CMIS-adapter.")
