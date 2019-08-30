import os

from django.core.exceptions import ImproperlyConfigured


def getenv(key, default=None, typecast=None, required=False, split=False):
    """
    Get the envvar ``key`` from the environment.
    """
    val = os.getenv(key, default)
    if required and val is None:
        raise ImproperlyConfigured("Envvar %s is required but not set." % key)

    if split and val:
        val = val.split(",")

    # figure out the target type from the default
    if default and not split and type(default) != str:
        typecast = type(default)

    if typecast is bool:
        val = handle_bool(val)
    elif typecast:
        if split:
            val = [typecast(x) for x in val]
        else:
            val = typecast(val)

    return val


def handle_bool(val) -> bool:
    if isinstance(val, bool):
        return val

    if isinstance(val, int):
        return val >= 1

    assert isinstance(val, str), "Expected string value"

    return val.lower() in ["yes", "true", "1"]
