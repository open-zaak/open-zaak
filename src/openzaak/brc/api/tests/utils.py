from django.conf import settings
from django.urls import reverse as _reverse, reverse_lazy as _reverse_lazy

from vng_api_common.tests import get_operation_url as _get_operation_url


def _inject_version(kwargs: dict):
    kwargs.setdefault('kwargs', {})
    kwargs['kwargs']['version'] = settings.REST_FRAMEWORK['DEFAULT_VERSION']


def reverse(*args, **kwargs):
    _inject_version(kwargs)
    return _reverse(*args, **kwargs)


def reverse_lazy(*args, **kwargs):
    _inject_version(kwargs)
    return _reverse_lazy(*args, **kwargs)


def get_operation_url(operation, **kwargs):
    return _get_operation_url(operation, spec_path=settings.SPEC_URL['BRC'], **kwargs)
