import inspect

from django.conf import settings
from django.db import models
from django.urls import reverse as _reverse, reverse_lazy as _reverse_lazy


def _magic_args(args, kwargs):
    """
    Do some trivial introspection to translate objects/models into common
    used urls.
    """
    if args and isinstance(args[0], models.Model):
        namespace = kwargs.pop("namespace", args[0]._meta.app_label)
        url_name = f"{namespace}:{args[0]._meta.model_name}-detail"
        kwargs["kwargs"].setdefault("uuid", args[0].uuid)
        args = (url_name,) + args[1:]
    elif args and inspect.isclass(args[0]) and issubclass(args[0], models.Model):
        namespace = kwargs.pop("namespace", args[0]._meta.app_label)
        url_name = f"{namespace}:{args[0]._meta.model_name}-list"
        args = (url_name,) + args[1:]
    return args, kwargs


def reverse(*args, **kwargs):
    """
    Determine the path for a named URL, instance or model.

    There's some 'magic' behaviour depending on the first arg provided:

    * if a model instance is provided, a detail URL is reversed
    * if a model class is provided, a list URL is reversed

    It is assumed that objects have a ``uuid`` field and the url kwarg is named
    ``uuid``. For nested routes, you need to provide the remaining parameters
    as kwargs. Other Django ``reverse`` params are passed down.
    """
    kwargs.setdefault("kwargs", {})
    kwargs["kwargs"]["version"] = settings.REST_FRAMEWORK["DEFAULT_VERSION"]
    args, kwargs = _magic_args(args, kwargs)
    return _reverse(*args, **kwargs)  # type: ignore


def reverse_lazy(*args, **kwargs):
    """
    Determine the path for a named URL, instance or model, lazily.

    There's some 'magic' behaviour depending on the first arg provided:

    * if a model instance is provided, a detail URL is reversed
    * if a model class is provided, a list URL is reversed

    It is assumed that objects have a ``uuid`` field and the url kwarg is named
    ``uuid``. For nested routes, you need to provide the remaining parameters
    as kwargs. Other Django ``reverse_lazy`` params are passed down.
    """
    kwargs.setdefault("kwargs", {})
    kwargs["kwargs"]["version"] = settings.REST_FRAMEWORK["DEFAULT_VERSION"]
    args, kwargs = _magic_args(args, kwargs)
    return _reverse_lazy(*args, **kwargs)  # type: ignore
