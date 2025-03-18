# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
"""
Continuous integration settings module.
"""
import os
import warnings

from urllib3.exceptions import SystemTimeWarning

from openzaak.notifications.tests.utils import LOGGING_SETTINGS

os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("SECRET_KEY", "dummy")
os.environ.setdefault("ENVIRONMENT", "CI")
os.environ.setdefault("SENDFILE_BACKEND", "django_sendfile.backends.simple")

from .includes.base import *  # noqa isort:skip

NOTIFICATIONS_DISABLED = True

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # See: https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "import_requests": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "import_requests",
    },
}

LOGGING = LOGGING_SETTINGS  # Minimally required logging is nice

# don't spend time on password hashing in tests/user factories
PASSWORD_HASHERS = ["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]

#
# Django-axes
#
AXES_BEHIND_REVERSE_PROXY = False

#
# Warning output
#
warnings.filterwarnings("ignore", r".*", SystemTimeWarning, "urllib3.connection")
