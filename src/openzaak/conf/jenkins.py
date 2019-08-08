from .base import *  # noqa

#
# Standard Django settings.
#

DEBUG = False

ADMINS = ()

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    # https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    'axes_cache': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

LOGGING['loggers'].update({
    'django': {
        'handlers': ['django'],
        'level': 'WARNING',
        'propagate': True,
    },
})

#
# Custom settings
#

# Show active environment in admin.
ENVIRONMENT = 'jenkins'

#
# Django-axes
#
AXES_BEHIND_REVERSE_PROXY = False  # Required to allow FakeRequest and the like to work correctly.
AXES_CACHE = 'axes_cache'

#
# Jenkins settings
#
INSTALLED_APPS += [
    'openzaak.tests',
    'django_jenkins',
]
PROJECT_APPS = [app for app in INSTALLED_APPS if app.startswith('openzaak.')]

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pylint',
    'django_jenkins.tasks.run_pep8',
)

NOTIFICATIONS_DISABLED = True
