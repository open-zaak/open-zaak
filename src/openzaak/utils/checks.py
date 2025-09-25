# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.conf import settings
from django.core.checks import Error, Warning, register
from django.http.request import validate_host

from furl.furl import furl


@register
def check_openzaak_domain(app_configs, **kwargs):
    if settings.SITE_DOMAIN:
        domain = settings.SITE_DOMAIN
    elif settings.OPENZAAK_DOMAIN:
        domain = settings.OPENZAAK_DOMAIN
    else:
        domain = ""

    errors = []

    try:
        parsed = furl(netloc=domain)
    except ValueError:
        invalid_netloc = True
    else:
        invalid_netloc = (
            parsed.scheme or parsed.path or parsed.username or parsed.password
        )

    if invalid_netloc:
        errors.append(
            Error(
                "The OPENZAAK_DOMAIN setting is invalid, it must be a valid DNS name "
                "with an optional port according to the pattern HOST[:PORT].",
                hint="Do not include scheme or path components.",
                id="openzaak.settings.E001",
            )
        )

    else:  # check against ALLOWED_HOSTS
        host = parsed.host.lower()
        if settings.OPENZAAK_REWRITE_HOST and not validate_host(
            host, settings.ALLOWED_HOSTS
        ):
            errors.append(
                Error(
                    f"The OPENZAAK_DOMAIN host ({host}) is not present in the "
                    "ALLOWED_HOSTS setting.",
                    hint=f"Add {host} to the ALLOWED_HOSTS setting.",
                    id="openzaak.settings.E002",
                )
            )

    if settings.OPENZAAK_REWRITE_HOST and settings.USE_X_FORWARDED_HOST:
        errors.append(
            Warning(
                "Setting OPENZAAK_REWRITE_HOST together with USE_X_FORWARDED_HOST causes "
                "the X-Forwarded-Host header to be ignored.",
                hint="Disable USE_X_FORWARDED_HOST or OPENZAAK_REWRITE_HOST",
                id="openzaak.settings.W001",
            )
        )

    return errors


@register
def check_zaak_identificatie_generator(app_configs, **kwargs):
    errors = []

    generator = settings.ZAAK_IDENTIFICATIE_GENERATOR
    options = settings.ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS

    if generator not in options:
        errors.append(
            Error(
                f"`{generator}` is not a valid value for the environment variable ZAAK_IDENTIFICATIE_GENERATOR.",
                hint=f"Set ZAAK_IDENTIFICATIE_GENERATOR to one of the following values: {list(options.keys())}.",
                id="openzaak.settings.E003",
            )
        )

    return errors
