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
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("OTEL_SERVICE_NAME", "openzaak-ci")

# S3 Storage
os.environ.setdefault("S3_USE_SSL", "no")
os.environ.setdefault("S3_ACCESS_KEY_ID", "minioadmin")
os.environ.setdefault("S3_SECRET_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")


from .includes.base import *  # noqa isort:skip

# Well-known authentication key to connect with Azurite
AZURE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

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
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

#
# Django-axes
#
AXES_BEHIND_REVERSE_PROXY = False

#
# Warning output
#
warnings.filterwarnings("ignore", r".*", SystemTimeWarning, "urllib3.connection")

# The combination of DB pooling enabled, tests running in parallel & the upgrade check
# (which runs queries?) causes the tests to fail.
if DB_POOL_ENABLED:
    INSTALLED_APPS.remove("upgrade_check")
