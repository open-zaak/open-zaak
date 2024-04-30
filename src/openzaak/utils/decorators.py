# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from functools import wraps

from django.core.cache import caches
from django.utils.translation import gettext_lazy as _

from drc_cmis.webservice.utils import NoURLMappingException, URLTooLongException

from openzaak.utils.exceptions import CMISAdapterException


def cache(key: str, alias: str = "default", **set_options):
    def decorator(func: callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            _cache = caches[alias]
            result = _cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            _cache.set(key, result, **set_options)
            return result

        return wrapped

    return decorator


def cache_uuid(key, timeout):
    def decorator(func: callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # use first argument of function to extract uuid
            uuid = args[0].split("/")[-1]
            key_uuid = f"{key}-{uuid}"
            cached_func = cache(key_uuid, timeout=timeout)(func)
            result = cached_func(*args, **kwargs)
            return result

        return wrapped

    return decorator


def convert_cmis_adapter_exceptions(function):
    """Convert exceptions raised by the CMIS-adapter to avoid 500 responses"""

    @wraps(function)
    def convert_exceptions(*args, **kwargs):
        try:
            response = function(*args, **kwargs)
        except NoURLMappingException:
            raise CMISAdapterException(
                _("CMIS-adapter could not shrink one of the URL fields.")
            )
        except URLTooLongException:
            raise CMISAdapterException(
                _("CMIS-adapter could not shrink a URL field below 100 characters.")
            )

        return response

    return convert_exceptions
