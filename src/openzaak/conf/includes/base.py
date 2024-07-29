# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import os

from notifications_api_common.settings import *  # noqa
from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config

from ...utils.monitoring import filter_sensitive_data
from .api import *  # noqa
from .plugins import PLUGIN_INSTALLED_APPS

init_sentry(before_send=filter_sensitive_data)

#
# Core Django settings
#

#
# DATABASE and CACHING setup
#
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("DB_NAME", "openzaak"),
        "USER": config("DB_USER", "openzaak"),
        "PASSWORD": config("DB_PASSWORD", "openzaak"),
        "HOST": config("DB_HOST", "localhost"),
        "PORT": config("DB_PORT", 5432),
    }
}

# Geospatial libraries
GEOS_LIBRARY_PATH = config("GEOS_LIBRARY_PATH", None)
GDAL_LIBRARY_PATH = config("GDAL_LIBRARY_PATH", None)

CACHES["import_requests"] = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "import_requests",
}

#
# APPLICATIONS enabled for this project
#
INSTALLED_APPS = (
    INSTALLED_APPS
    + [
        # Optional applications.
        "django.contrib.gis",
        # External applications.
        "django_db_logger",
        "vng_api_common.authorizations",
        "vng_api_common.audittrails",
        "vng_api_common.notifications",
        "rest_framework_gis",
        "sniplates",  # TODO can this be removed?
        "django_better_admin_arrayfield",  # TODO can this be removed?
        "django_loose_fk",
        "drc_cmis",
        # Project applications.
        "openzaak.accounts",
        "openzaak.import_data",
        "openzaak.utils",
        "openzaak.components.autorisaties",
        "openzaak.components.zaken",
        "openzaak.components.besluiten",
        "openzaak.components.documenten",
        "openzaak.components.catalogi",
        "openzaak.config",
        "openzaak.selectielijst",
        "openzaak.notifications",
    ]
    + PLUGIN_INSTALLED_APPS
)

MIDDLEWARE = [
    "openzaak.utils.middleware.OverrideHostMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "openzaak.utils.middleware.LogHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # 'django.middleware.locale.LocaleMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "openzaak.components.autorisaties.middleware.AuthMiddleware",
    "mozilla_django_oidc_db.middleware.SessionRefresh",
    "maykin_2fa.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "openzaak.utils.middleware.APIVersionHeaderMiddleware",
    "openzaak.utils.middleware.DeprecationMiddleware",
    "openzaak.utils.middleware.EnabledMiddleware",
    "axes.middleware.AxesMiddleware",
]

#
# SERVING of static and media files
#

#
# Sending EMAIL
#

#
# LOGGING
#
LOGGING["filters"]["failed_notification"] = {
    "()": "openzaak.notifications.filters.FailedNotificationFilter"
}
LOGGING["handlers"]["failed_notification"] = {
    "level": "DEBUG",
    "filters": ["failed_notification"],
    "class": "openzaak.notifications.handlers.DatabaseLogHandler",
}
LOGGING["loggers"]["notifications_api_common.tasks"] = {
    "handlers": [
        "failed_notification",  # always log this to the database!
        *logging_root_handlers,
    ],
    "level": "WARNING",
    "propagate": True,
}

#
# AUTH settings - user accounts, passwords, backends...
#

#
# Custom settings
#
PROJECT_NAME = "Open Zaak"
SITE_TITLE = "API dashboard"

# if specified, this replaces the host information in the requests, and it is used
# to build absolute URLs.
OPENZAAK_DOMAIN = config("OPENZAAK_DOMAIN", "")
OPENZAAK_REWRITE_HOST = config("OPENZAAK_REWRITE_HOST", False)

# settings for uploading large files
MIN_UPLOAD_SIZE = config("MIN_UPLOAD_SIZE", 4 * 2**30)
# default to the MIN_UPLOAD_SIZE, as that is typically the maximum post body size configured
# in the webserver
DOCUMENTEN_UPLOAD_CHUNK_SIZE = config("DOCUMENTEN_UPLOAD_CHUNK_SIZE", MIN_UPLOAD_SIZE)
DOCUMENTEN_UPLOAD_READ_CHUNK = config(
    "DOCUMENTEN_UPLOAD_READ_CHUNK", 6 * 2**20
)  # 6 MB default
DOCUMENTEN_UPLOAD_DEFAULT_EXTENSION = "bin"

# Change the User-Agent value for the outgoing requests
USER_AGENT = "Open Zaak"

# urls for OAS3 specifications
SPEC_URL = {
    "zaken": os.path.join(
        BASE_DIR, "src", "openzaak", "components", "zaken", "openapi.yaml"
    ),
    "besluiten": os.path.join(
        BASE_DIR, "src", "openzaak", "components", "besluiten", "openapi.yaml"
    ),
    "documenten": os.path.join(
        BASE_DIR, "src", "openzaak", "components", "documenten", "openapi.yaml"
    ),
    "catalogi": os.path.join(
        BASE_DIR, "src", "openzaak", "components", "catalogi", "openapi.yaml"
    ),
    "autorisaties": os.path.join(
        BASE_DIR, "src", "openzaak", "components", "autorisaties", "openapi.yaml"
    ),
}

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# DJANGO-PRIVATES -- safely serve files after authorization
#

# requires an nginx container running in front
SENDFILE_BACKEND = config("SENDFILE_BACKEND", "django_sendfile.backends.nginx")
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = PRIVATE_MEDIA_URL

#
# ZGW-CONSUMERS
#
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "tests", "schemas"),
    os.path.join(DJANGO_PROJECT_DIR, "selectielijst", "tests", "files"),
    os.path.join(DJANGO_PROJECT_DIR, "notifications", "tests", "files"),
]
ZGW_CONSUMERS_CLIENT_CLASS = "openzaak.client.OpenZaakClient"

#
# DJANGO-LOOSE-FK -- handle internal and external API resources
#
DEFAULT_LOOSE_FK_LOADER = "openzaak.loaders.AuthorizedRequestsLoader"
LOOSE_FK_LOCAL_BASE_URLS = config("LOOSE_FK_LOCAL_BASE_URLS", split=True, default=[])

#
# MAYKIN-2FA
#
# Uses django-two-factor-auth under the hood, so relevant upstream package settings
# apply too.
#

# Relying Party name for WebAuthn (hardware tokens)
TWO_FACTOR_WEBAUTHN_RP_NAME = "Open Zaak - admin"

#
# Django setup configuration
#
SETUP_CONFIGURATION_STEPS = [
    "openzaak.config.bootstrap.site.SiteConfigurationStep",
    "openzaak.config.bootstrap.notifications.AuthNotificationStep",
    "openzaak.config.bootstrap.notifications.NotificationsAPIConfigurationStep",
    "openzaak.config.bootstrap.selectielijst.SelectielijstAPIConfigurationStep",
    "openzaak.config.bootstrap.demo.DemoUserStep",
]

#
# OpenZaak configuration
#


STORE_FAILED_NOTIFS = True

# Expiry time in seconds for JWT
JWT_EXPIRY = config("JWT_EXPIRY", default=3600)
# leeway when comparing timestamps - non-zero value account for clock drift
JWT_LEEWAY = config("JWT_LEEWAY", default=0)

CUSTOM_CLIENT_FETCHER = "openzaak.utils.auth.get_client"

CMIS_ENABLED = config("CMIS_ENABLED", default=False)
CMIS_MAPPER_FILE = config(
    "CMIS_MAPPER_FILE", default=os.path.join(BASE_DIR, "config", "cmis_mapper.json")
)
CMIS_URL_MAPPING_ENABLED = config("CMIS_URL_MAPPING_ENABLED", default=False)

# Name of the cache used to store responses for requests made when importing catalogi
IMPORT_REQUESTS_CACHE_NAME = config("IMPORT_REQUESTS_CACHE_NAME", "import_requests")

ZAAK_EIGENSCHAP_WAARDE_VALIDATION = config(
    "ZAAK_EIGENSCHAP_WAARDE_VALIDATION", default=False
)
# improve performance by removing exact count from pagination
FUZZY_PAGINATION = config("FUZZY_PAGINATION", default=False)
# maximum number of objects where exact count is calculated in pagination when FUZZY_PAGINATION is on
FUZZY_PAGINATION_COUNT_LIMIT = config("FUZZY_PAGINATION_COUNT_LIMIT", default=500)

# Import settings
IMPORT_DOCUMENTEN_BASE_DIR = config("IMPORT_DOCUMENTEN_BASE_DIR", BASE_DIR)
IMPORT_DOCUMENTEN_BATCH_SIZE = config("IMPORT_DOCUMENTEN_BATCH_SIZE", 500)

# Settings for setup_configuration command
# sites config
SITES_CONFIG_ENABLE = config("SITES_CONFIG_ENABLE", default=True)
OPENZAAK_ORGANIZATION = config("OPENZAAK_ORGANIZATION", "")
# notif -> OZ config
NOTIF_OPENZAAK_CONFIG_ENABLE = config("NOTIF_OPENZAAK_CONFIG_ENABLE", default=True)
NOTIF_OPENZAAK_CLIENT_ID = config("NOTIF_OPENZAAK_CLIENT_ID", "")
NOTIF_OPENZAAK_SECRET = config("NOTIF_OPENZAAK_SECRET", "")
# OZ -> notif config
OPENZAAK_NOTIF_CONFIG_ENABLE = config("OPENZAAK_NOTIF_CONFIG_ENABLE", default=True)
NOTIF_API_ROOT = config("NOTIF_API_ROOT", "")
if NOTIF_API_ROOT and not NOTIF_API_ROOT.endswith("/"):
    NOTIF_API_ROOT = f"{NOTIF_API_ROOT.strip()}/"
NOTIF_API_OAS = config("NOTIF_API_OAS", default=f"{NOTIF_API_ROOT}schema/openapi.yaml")
OPENZAAK_NOTIF_CLIENT_ID = config("OPENZAAK_NOTIF_CLIENT_ID", "")
OPENZAAK_NOTIF_SECRET = config("OPENZAAK_NOTIF_SECRET", "")
# Selectielijst config
OPENZAAK_SELECTIELIJST_CONFIG_ENABLE = config(
    "OPENZAAK_SELECTIELIJST_CONFIG_ENABLE", default=True
)
SELECTIELIJST_API_ROOT = config(
    "SELECTIELIJST_API_ROOT", default="https://selectielijst.openzaak.nl/api/v1/"
)
if SELECTIELIJST_API_ROOT and not SELECTIELIJST_API_ROOT.endswith("/"):
    SELECTIELIJST_API_ROOT = f"{SELECTIELIJST_API_ROOT.strip()}/"
SELECTIELIJST_API_OAS = config(
    "SELECTIELIJST_API_OAS", default=f"{SELECTIELIJST_API_ROOT}schema/openapi.yaml"
)
SELECTIELIJST_ALLOWED_YEARS = config(
    "SELECTIELIJST_ALLOWED_YEARS", default=[2017, 2020]
)
SELECTIELIJST_DEFAULT_YEAR = config("SELECTIELIJST_DEFAULT_YEAR", default=2020)
# Demo user config
DEMO_CONFIG_ENABLE = config("DEMO_CONFIG_ENABLE", default=DEBUG)
DEMO_CLIENT_ID = config("DEMO_CLIENT_ID", "")
DEMO_SECRET = config("DEMO_SECRET", "")
