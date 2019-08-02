from django.conf import settings
from django.urls import reverse as _reverse
from vng_api_common.tests import get_operation_url as _get_operation_url


def reverse(*args, **kwargs):
    kwargs.setdefault('kwargs', {})
    kwargs['kwargs']['version'] = settings.REST_FRAMEWORK['DEFAULT_VERSION']
    return _reverse(*args, **kwargs)


def get_operation_url(operation, **kwargs):
    return _get_operation_url(operation, spec_path=settings.SPEC_URL['zaken'], **kwargs)
