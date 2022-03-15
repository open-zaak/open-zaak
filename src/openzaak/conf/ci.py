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

from .includes.base import *  # noqa isort:skip

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # See: https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "kic_sync": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

LOGGING = LOGGING_SETTINGS  # Minimally required logging is nice

ENVIRONMENT = "CI"

#
# Django-axes
#
AXES_BEHIND_REVERSE_PROXY = False

#
# Open Zaak specific settings
#
NOTIFICATIONS_DISABLED = True

#
# Warning output
#
warnings.filterwarnings("ignore", r".*", SystemTimeWarning, "urllib3.connection")
