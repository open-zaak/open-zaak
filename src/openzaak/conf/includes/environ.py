# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from decouple import Csv, config as _config, undefined
from sentry_sdk.integrations import DidNotEnable, django, redis


def config(option: str, default=undefined, *args, **kwargs):
    if "split" in kwargs:
        kwargs.pop("split")
        kwargs["cast"] = Csv()
        if default == []:
            default = ""

    if default is not undefined and default is not None:
        kwargs.setdefault("cast", type(default))
    return _config(option, default=default, *args, **kwargs)


def get_sentry_integrations() -> list:
    """
    Determine which Sentry SDK integrations to enable.
    """
    default = [
        django.DjangoIntegration(),
        redis.RedisIntegration(),
    ]
    extra = []

    try:
        from sentry_sdk.integrations import celery
    except DidNotEnable:  # happens if the celery import fails by the integration
        pass
    else:
        extra.append(celery.CeleryIntegration())

    return [*default, *extra]


def strip_protocol_from_origin(origin: str) -> str:
    parsed = urlparse(origin)
    return parsed.netloc
