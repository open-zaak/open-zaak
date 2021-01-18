# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from functools import wraps

from django.core.cache import caches


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
