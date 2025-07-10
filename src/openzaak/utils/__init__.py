# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import warnings
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

import dateutil.parser
from django_loose_fk.virtual_models import ProxyMixin
from furl import furl


def parse_isodatetime(val) -> datetime:
    return dateutil.parser.parse(val)


def get_openzaak_domain() -> str:
    """
    Obtain the domain/netloc of Open Zaak according to settings or configuration.
    """
    from django.contrib.sites.models import Site

    if settings.SITE_DOMAIN:
        return settings.SITE_DOMAIN

    warnings.warn(
        "Deriving the domain from the `OPENZAAK_DOMAIN` and `Sites` configuration will soon be deprecated, "
        "please migrate to the SITE_DOMAIN setting.",
        PendingDeprecationWarning,
    )

    if settings.OPENZAAK_DOMAIN:
        return settings.OPENZAAK_DOMAIN

    return Site.objects.get_current().domain


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


def get_loose_fk_object_url(instance, request):
    from vng_api_common.tests import reverse

    if isinstance(instance, ProxyMixin):
        return instance._loose_fk_data["url"]

    path = reverse(instance)
    return build_absolute_url(path, request)
