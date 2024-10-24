# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import os
import sys
import warnings

from django.core.paginator import UnorderedObjectListWarning

from urllib3.exceptions import SystemTimeWarning

os.environ.setdefault("DEBUG", "yes")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault(
    "SECRET_KEY", "8u9chcd4g1%i5z)u@s6#c#0u%s_gggx*915w(yzrf#awezmu^i"
)
os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("RELEASE", "dev")
os.environ.setdefault("ENVIRONMENT", "development")

os.environ.setdefault("DB_NAME", "openzaak")
os.environ.setdefault("DB_USER", "openzaak")
os.environ.setdefault("DB_PASSWORD", "openzaak")

os.environ.setdefault("SENDFILE_BACKEND", "django_sendfile.backends.development")

os.environ.setdefault("ZTC_JWT_SECRET", "open-to-ztc")
os.environ.setdefault("ZRC_JWT_SECRET", "open-to-zrc")
os.environ.setdefault("NUM_PROXIES", "0")

from .includes.base import *  # noqa isort:skip

#
# Standard Django settings.
#
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

LOGGING["loggers"].update(
    {
        "openzaak": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "drc_cmis": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "django": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "performance": {"handlers": ["console"], "level": "INFO", "propagate": True},
    }
)

if not LOG_QUERIES:
    LOGGING["loggers"]["django.db.backends"]["handlers"] = ["django"]

#
# Library settings
#

# Django debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ("127.0.0.1",)
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

# in memory cache and django-axes don't get along.
# https://django-axes.readthedocs.io/en/latest/configuration.html#known-configuration-problems
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "import_requests": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "import_requests",
    },
}

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "rest_framework.renderers.BrowsableAPIRenderer",
)

#
# DJANGO-SILK
#
if config("PROFILE", default=False, add_to_docs=False):
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE
    security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE.insert(security_index + 1, "whitenoise.middleware.WhiteNoiseMiddleware")

warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

warnings.filterwarnings(
    "error",
    r"Pagination may yield inconsistent results with an unordered object_list: .*",
    UnorderedObjectListWarning,
    r"rest_framework\.pagination",
)

if "test" in sys.argv:
    NOTIFICATIONS_DISABLED = True

    warnings.filterwarnings("ignore", r".*", SystemTimeWarning, "urllib3.connection")

ELASTIC_APM["DEBUG"] = config("DISABLE_APM_IN_DEV", default=True, add_to_docs=False)

# Override settings with local settings.
try:
    from .includes.local import *  # noqa
except ImportError:
    pass
