# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

import dateutil.parser
from furl import furl


def parse_isodatetime(val) -> datetime:
    return dateutil.parser.parse(val)


def get_openzaak_domain() -> str:
    """
    Obtain the domain/netloc of Open Zaak according to settings or configuration.
    """
    return settings.OPENZAAK_DOMAIN


def build_absolute_url(path: str, request: Optional[HttpRequest] = None) -> str:
    if request is not None:
        return request.build_absolute_uri(path)

    domain = get_openzaak_domain()
    _furl = furl(
        scheme="https" if settings.IS_HTTPS else "http",
        netloc=domain,
        path=path,
    )
    return _furl.url


def build_fake_request(*, method="get", **kwargs) -> HttpRequest:
    from rest_framework.test import APIRequestFactory

    request_factory = APIRequestFactory()

    environ = {
        "wsgi.url_scheme": "https" if settings.IS_HTTPS else "http",
        "HTTP_HOST": get_openzaak_domain(),
    }
    environ.update(kwargs)
    func = getattr(request_factory, method.lower())
    return func("/", **environ)
