"""
Production environment settings module.

Tweaks the base settings so that caching mechanisms are used where possible,
and HTTPS is leveraged where possible to further secure things.
"""
from .includes.base import *  # noqa

# Caching sessions.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Caching templates.
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    ("django.template.loaders.cached.Loader", TEMPLATE_LOADERS)
]

# The file storage engine to use when collecting static files with the
# collectstatic management command.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Production logging facility.
root_handler = "sentry" if "sentry" in LOGGING["handlers"] else "project"
LOGGING["loggers"].update(
    {
        "": {"handlers": [root_handler], "level": "ERROR", "propagate": False},
        "django": {"handlers": ["django"], "level": "INFO", "propagate": True},
        "django.security.DisallowedHost": {
            "handlers": ["django"],
            "level": "CRITICAL",
            "propagate": False,
        },
    }
)

# Only set this when we're behind a reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True  # Sets X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True  # Sets X-XSS-Protection: 1; mode=block

# Deal with being hosted on a subpath
subpath = config("SUBPATH", None)
if subpath:
    if not subpath.startswith("/"):
        subpath = f"/{subpath}"

    FORCE_SCRIPT_NAME = subpath
    STATIC_URL = f"{FORCE_SCRIPT_NAME}{STATIC_URL}"
    MEDIA_URL = f"{FORCE_SCRIPT_NAME}{MEDIA_URL}"

#
# Custom settings overrides
#
ENVIRONMENT = "production"
ENVIRONMENT_SHOWN_IN_ADMIN = False
