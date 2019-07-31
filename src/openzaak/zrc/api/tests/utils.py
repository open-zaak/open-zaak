from django.conf import settings
from django.urls import reverse as _reverse


def reverse(*args, **kwargs):
    kwargs.setdefault('kwargs', {})
    kwargs['kwargs']['version'] = settings.REST_FRAMEWORK['DEFAULT_VERSION']
    return _reverse(*args, **kwargs)
