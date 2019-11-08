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
