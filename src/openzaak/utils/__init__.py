# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import warnings
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

import dateutil.parser
from furl import furl

default_app_config = "openzaak.utils.apps.UtilsConfig"


def parse_isodatetime(val) -> datetime:
    return dateutil.parser.parse(val)


def build_absolute_url(path: str, request: Optional[HttpRequest] = None) -> str:
    from django.contrib.sites.models import Site

    if request is not None:
        return request.build_absolute_uri(path)

    if settings.OPENZAAK_DOMAIN:
        domain = settings.OPENZAAK_DOMAIN
    else:
        warnings.warn(
            "Deriving the domain from the Site configuration will soon be deprecated, "
            "please migrate to the OPENZAAK_DOMAIN setting.",
            PendingDeprecationWarning,
        )
        domain = Site.objects.get_current().domain

    _furl = furl(
        scheme="https" if settings.IS_HTTPS else "http", netloc=domain, path=path,
    )
    return _furl.url
