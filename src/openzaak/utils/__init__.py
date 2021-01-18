# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

import dateutil.parser

default_app_config = "openzaak.utils.apps.UtilsConfig"


def parse_isodatetime(val) -> datetime:
    return dateutil.parser.parse(val)


def build_absolute_url(path: str, request: Optional[HttpRequest] = None) -> str:
    from django.contrib.sites.models import Site

    if request is not None:
        return request.build_absolute_uri(path)

    domain = Site.objects.get_current().domain
    protocol = "https" if settings.IS_HTTPS else "http"
    return f"{protocol}://{domain}{path}"
