# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import os
from pathlib import Path

import sentry_sdk
import structlog
from celery.schedules import crontab
from notifications_api_common.settings import *  # noqa
from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config, get_sentry_integrations

from openzaak.utils.monitoring import filter_sensitive_data

from .api import *  # noqa
from .plugins import PLUGIN_INSTALLED_APPS

# Reinitialize Sentry to add the before_send hook
if SENTRY_DSN:
    SENTRY_CONFIG["before_send"] = filter_sensitive_data
    sentry_sdk.init(
        **SENTRY_CONFIG,
        integrations=get_sentry_integrations(),
        send_default_pii=True,
    )


#
# Core Django settings
#

#
# DATABASE and CACHING setup
#

DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = config(
    "DB_DISABLE_SERVER_SIDE_CURSORS",
    False,
    help_text=(
        "Whether or not server side cursors should be disabled for Postgres connections. "
        "Setting this to true is required when using a connection pooler in "
        "transaction mode (like PgBouncer). "
        "**WARNING:** the effect of disabling server side cursors on performance has not "
        "been thoroughly tested yet."
    ),
    group="Database",
)

# Define this variable here to ensure it shows up in the envvar documentation
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# Geospatial libraries
GEOS_LIBRARY_PATH = config(
    "GEOS_LIBRARY_PATH",
    None,
    help_text=(
        "Full path to the GEOS library used by GeoDjango. In most circumstances, this can be left empty."
    ),
)
GDAL_LIBRARY_PATH = config(
    "GDAL_LIBRARY_PATH",
    None,
    help_text=(
        "Full path to the GDAL library used by GeoDjango. In most circumstances, this can be left empty."
    ),
)

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
        # `django.contrib.sites` added at the project level because it has been removed at the packages level.
        # This component is deprecated and should be completely removed.
        # To determine the project's domain, use the `SITE_DOMAIN` environment variable.
        "django.contrib.sites",
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
        "django_celery_beat",
        "django_structlog",
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
    "sessionprofile.middleware.SessionProfileMiddleware",
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
    "csp.contrib.rate_limiting.RateLimitedCSPMiddleware",
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


# XXX: this should be renamed to `LOG_REQUESTS` in the next major release
_log_requests_via_middleware = config(
    "ENABLE_STRUCTLOG_REQUESTS",
    default=True,
    help_text=("enable structured logging of requests"),
    group="Logging",
)
if _log_requests_via_middleware:
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
        "django_structlog.middlewares.RequestMiddleware",
    )

# TODO move this back to OAF
# Override LOGGING, because OAF does not yet apply structlog for all components
logging_root_handlers = ["console"] if LOG_STDOUT else ["json_file"]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # structlog - foreign_pre_chain handles logs coming from stdlib logging module,
        # while the `structlog.configure` call handles everything coming from structlog.
        # They are mutually exclusive.
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
            ],
        },
        "plain_console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
            ],
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {"format": "%(asctime)s %(process)d | %(thread)d | %(message)s"},
        "db": {"format": "%(asctime)s | %(message)s"},
        "outgoing_requests": {"()": HttpFormatter},
    },
    # TODO can be removed?
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        # TODO can be removed?
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": config(
                "LOG_FORMAT_CONSOLE",
                default="json",
                help_text=(
                    "The format for the console logging handler, possible options: ``json``, ``plain_console``."
                ),
                group="Logging",
            ),
        },
        "console_db": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "db",
        },
        # replaces the "django" and "project" handlers - in containerized applications
        # the best practices is to log to stdout (use the console handler).
        "json_file": {
            "level": LOG_LEVEL,  # always debug might be better?
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGGING_DIR) / "application.jsonl",
            "formatter": "json",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGGING_DIR) / "performance.log",
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "requests": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOGGING_DIR) / "requests.log",
            "formatter": "timestamped",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "log_outgoing_requests": {
            "level": "DEBUG",
            "formatter": "outgoing_requests",
            "class": "logging.StreamHandler",  # to write to stdout
        },
        "save_outgoing_requests": {
            "level": "DEBUG",
            # enabling saving to database
            "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": logging_root_handlers,
            "level": "ERROR",
            "propagate": False,
        },
        PROJECT_DIRNAME: {
            "handlers": logging_root_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "mozilla_django_oidc": {
            "handlers": logging_root_handlers,
            "level": LOG_LEVEL,
        },
        f"{PROJECT_DIRNAME}.utils.middleware": {
            "handlers": logging_root_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "vng_api_common": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["console_db"] if LOG_QUERIES else [],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": logging_root_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # suppress django.server request logs because those are already emitted by
        # django-structlog middleware
        "django.server": {
            "handlers": ["console"],
            "level": "WARNING" if _log_requests_via_middleware else "INFO",
            "propagate": False,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "log_outgoing_requests": {
            "handlers": (
                ["log_outgoing_requests", "save_outgoing_requests"]
                if LOG_REQUESTS
                else []
            ),
            "level": "DEBUG",
            "propagate": True,
        },
        "django_structlog": {
            "handlers": logging_root_handlers,
            "level": "INFO",
            "propagate": False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # structlog.processors.ExceptionPrettyPrinter(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


#
# DJANGO-STRUCTLOG
#
DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False
DJANGO_STRUCTLOG_CELERY_ENABLED = True

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
# This variable is deprecated; the `SITE_DOMAIN` variable should be used instead.
OPENZAAK_DOMAIN = config(
    "OPENZAAK_DOMAIN",
    "",
    help_text=(
        "a [host]:[port] or [host] value indicating the canonical domain where Open Zaak "
        "is hosted/deployed, e.g. ``openzaak.example.com:8443``. This value is used "
        "(together with IS_HTTPS) when fully qualified URLs need to be constructed "
        "without HTTP request context available. "
        "Deriving the domain from the ``OPENZAAK_DOMAIN`` and ``Sites`` configuration will soon be deprecated, "
        "please migrate to the ``SITE_DOMAIN`` setting."
    ),
    auto_display_default=False,
)

OPENZAAK_REWRITE_HOST = config(
    "OPENZAAK_REWRITE_HOST",
    False,
    help_text=(
        "whether to rewrite the request host of all incoming requests with the value of "
        "OPENZAAK_DOMAIN, discarding the original Host header or headers set by reverse "
        "proxies. Useful if you provide the services only via the NLX network, "
        "for example. Defaults to False and conflicts with ``USE_X_FORWARDED_HOST``."
    ),
    auto_display_default=False,
)

# settings for uploading large files
MIN_UPLOAD_SIZE = config(
    "MIN_UPLOAD_SIZE",
    4 * 2**30,
    help_text=(
        "the max allowed size of POST bodies, in bytes. Defaults to 4GiB. "
        "Note that you should also configure your web server to allow this."
    ),
)
# default to the MIN_UPLOAD_SIZE, as that is typically the maximum post body size configured
# in the webserver
DOCUMENTEN_UPLOAD_CHUNK_SIZE = config(
    "DOCUMENTEN_UPLOAD_CHUNK_SIZE",
    MIN_UPLOAD_SIZE,
    help_text=(
        "chunk size in bytes for large file uploads - determines the size for a single "
        " upload chunk. Note that making this larger than ``MIN_UPLOAD_SIZE`` breaks large file uploads"
    ),
)
DOCUMENTEN_UPLOAD_READ_CHUNK = config(
    "DOCUMENTEN_UPLOAD_READ_CHUNK",
    6 * 2**20,
    help_text=(
        "chunk size in bytes for large file uploads - when merging upload chunks, this "
        "determines the number of bytes read to copy to the destination file. Defaults to 6 MiB."
    ),
    auto_display_default=False,
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
SENDFILE_BACKEND = config(
    "SENDFILE_BACKEND",
    "django_sendfile.backends.nginx",
    help_text=(
        "which backend to use for authorization-secured upload downloads. Defaults to "
        "sendfile.backends.nginx. See `django-sendfile2 <https://pypi.org/project/django-sendfile2/>`_ "
        "for available backends"
    ),
)
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = PRIVATE_MEDIA_URL

#
# ZGW-CONSUMERS-OAS
#
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "tests", "schemas"),
    os.path.join(DJANGO_PROJECT_DIR, "selectielijst", "tests", "files"),
    os.path.join(DJANGO_PROJECT_DIR, "notifications", "tests", "files"),
]

#
# DJANGO-LOOSE-FK -- handle internal and external API resources
#
DEFAULT_LOOSE_FK_LOADER = "openzaak.loaders.AuthorizedRequestsLoader"
LOOSE_FK_LOCAL_BASE_URLS = config(
    "LOOSE_FK_LOCAL_BASE_URLS",
    split=True,
    default=[],
    help_text=(
        "explicitly list the allowed prefixes of local urls. "
        "Defaults to an empty list. This setting can be used to separate local and external urls, when "
        "Open Zaak and other services are deployed within the same domain or API Gateway. "
        "If this setting is not defined, all urls with the same host as in the request are "
        "considered local. Example: "
        "``LOOSE_FK_LOCAL_BASE_URLS=http://api.example.nl/ozgv-t/zaken/,"
        "http://api.example.nl/ozgv-t/catalogi/,http://api.example.nl/ozgv-t/autorisaties/``"
    ),
)

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
    "django_setup_configuration.contrib.sites.steps.SitesConfigurationStep",
    "mozilla_django_oidc_db.setup_configuration.steps.AdminOIDCConfigurationStep",
    "zgw_consumers.contrib.setup_configuration.steps.ServiceConfigurationStep",
    "openzaak.config.setup_configuration.steps.SelectielijstAPIConfigurationStep",
    "vng_api_common.contrib.setup_configuration.steps.JWTSecretsConfigurationStep",
    "vng_api_common.contrib.setup_configuration.steps.ApplicatieConfigurationStep",
    "notifications_api_common.contrib.setup_configuration.steps.NotificationConfigurationStep",
]

#
# self-certifi
#
# To make sure these variables appear in the documentation
config(
    "EXTRA_VERIFY_CERTS",
    "",
    help_text=(
        "a comma-separated list of paths to certificates to trust, "
        "If you're using self-signed certificates for the services that Open Notificaties "
        "communicates with, specify the path to those (root) certificates here, rather than "
        "disabling SSL certificate verification. Example: "
        "``EXTRA_VERIFY_CERTS=/etc/ssl/root1.crt,/etc/ssl/root2.crt``."
    ),
    auto_display_default=False,
)
config(
    "CURL_CA_BUNDLE",
    "",
    help_text=(
        "if this variable is set to an empty string, it disables SSL/TLS certificate "
        "verification. Even calls from Open Zaak to other services "
        "such as the `Selectie Lijst`_ will be disabled, so this "
        "variable should be used with care to prevent unwanted side-effects."
    ),
    auto_display_default=False,
)

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Note that by default UTC times are used here (see `nowfun` kwarg)
CELERY_BEAT_SCHEDULE = {
    "daily-remove-imports": {
        "task": "openzaak.import_data.tasks.remove_imports",
        "schedule": crontab(hour="9"),
    }
}
CELERY_RESULT_EXPIRES = config(
    "CELERY_RESULT_EXPIRES",
    3600,
    help_text=(
        "How long the results of tasks will be stored in Redis (in seconds),"
        " this can be set to a lower duration to lower memory usage for Redis."
    ),
    group="Celery",
)

#
# DJANGO-CSP
#
CSP_CONNECT_SRC = CSP_DEFAULT_SRC + ["raw.githubusercontent.com"]
CSP_SCRIPT_SRC = CSP_SCRIPT_SRC + ["cdnjs.cloudflare.com", "cdn.jsdelivr.net"]
CSP_IMG_SRC = CSP_IMG_SRC + ["cdnjs.cloudflare.com", "tile.openstreetmap.org"]
CSP_STYLE_SRC = CSP_STYLE_SRC + ["cdnjs.cloudflare.com", "cdn.jsdelivr.net"]

# TODO is there a better way to fix this?
CSP_INCLUDE_NONCE_IN.remove("script-src")  # error with GISModelAdmin.
CSP_INCLUDE_NONCE_IN.remove("style-src")  # error with redoc.
#
# OpenZaak configuration
#


ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS = {
    "use-creation-year": "openzaak.components.zaken.api.utils.generate_zaak_identificatie_with_creation_year",
    "use-start-datum-year": "openzaak.components.zaken.api.utils.generate_zaak_identificatie_with_start_datum_year",
}

ZAAK_IDENTIFICATIE_GENERATOR = config(
    "ZAAK_IDENTIFICATIE_GENERATOR",
    default="use-start-datum-year",
    help_text=(
        "The method of **Zaak.identificatie** generation. Possible values are: "
        f"{', '.join(f'``{opt}``' for opt in ZAAK_IDENTIFICATIE_GENERATOR_OPTIONS)} "
    ),
)

STORE_FAILED_NOTIFS = True
# silence using upper case in enums
SILENCED_SYSTEM_CHECKS = SILENCED_SYSTEM_CHECKS + ["vng_api_common.enums.W001"]

# Expiry time in seconds for JWT
JWT_EXPIRY = config(
    "JWT_EXPIRY",
    default=3600,
    help_text="duration a JWT is considered to be valid, in seconds.",
)
# leeway when comparing timestamps - non-zero value account for clock drift
# This variable is deprecated; the `TIME_LEEWAY` variable should be used for everything instead.
JWT_LEEWAY = config(
    "JWT_LEEWAY",
    default=0,
    help_text=(
        "JWT validation has a time aspect, usually in the form of the ``iat`` and "
        "``nbf`` claims. Clock drift between server and client can occur. This setting allows "
        "specifying the leeway in seconds, and defaults to ``0`` (no leeway). It is advised to "
        "not make this larger than a couple of minutes."
        "setting a leeway using ``JWT_LEEWAY`` will soon be deprecated, "
        "please migrate to the ``TIME_LEEWAY`` setting."
    ),
    auto_display_default=False,
)

TIME_LEEWAY = config(
    "TIME_LEEWAY",
    default=JWT_LEEWAY,
    help_text=(
        "Some validation & JWT validation has a time aspect (usually in the form of the ``iat`` and "
        "``nbf`` claims). Clock drift between server and client can occur. This setting allows "
        "specifying the leeway in seconds, and defaults to ``0`` (no leeway). It is advised to "
        "not make this larger than a couple of minutes."
    ),
)


CMIS_ENABLED = config(
    "CMIS_ENABLED",
    default=False,
    help_text=("whether to enable the CMIS adapter"),
    group="CMIS",
)
CMIS_MAPPER_FILE = config(
    "CMIS_MAPPER_FILE",
    default=os.path.join(BASE_DIR, "config", "cmis_mapper.json"),
    help_text=(
        "name of the file containing the mapping between the Django and Document Management System names "
        "for document properties. See the installation section for more details. "
        "Defaults to the absolute path of ``open-zaak/config/cmis_mapper.json``."
    ),
    auto_display_default=False,
    group="CMIS",
)
CMIS_URL_MAPPING_ENABLED = config(
    "CMIS_URL_MAPPING_ENABLED",
    default=False,
    help_text="enable the URL shortener when using the CMIS adapter",
    group="CMIS",
)

ZAAK_EIGENSCHAP_WAARDE_VALIDATION = config(
    "ZAAK_EIGENSCHAP_WAARDE_VALIDATION",
    default=False,
    help_text=(
        "if this variable is set to ``true``, ``yes`` or ``1``, ``ZaakEigenschap.waarde`` "
        "property would be validated against the related ``Eigenschap.specificatie``."
    ),
)
# improve performance by removing exact count from pagination
FUZZY_PAGINATION = config(
    "FUZZY_PAGINATION",
    default=False,
    help_text=(
        "if this variable is set to ``true``, ``yes`` or ``1``, fuzzy pagination will be applied "
        "to all paginated API endpoints. This is to optimize performance of the endpoints and results in "
        "the ``count`` property to return a non-exact (fuzzy) value."
    ),
)
FUZZY_PAGINATION_COUNT_LIMIT = config(
    "FUZZY_PAGINATION_COUNT_LIMIT",
    default=500,
    help_text=(
        "an integer value to indicate the maximum number of objects where the exact "
        "count is calculated in pagination when ``FUZZY_PAGINATION`` is enabled"
    ),
)

# Import settings
IMPORT_RETENTION_DAYS = config(
    "IMPORT_RETENTION_DAYS",
    7,
    help_text=(
        "an integer which specifies the number of days after which ``Import`` "
        "instances will be deleted."
    ),
    group="Documenten import",
)
IMPORT_DOCUMENTEN_BASE_DIR = config(
    "IMPORT_DOCUMENTEN_BASE_DIR",
    BASE_DIR,
    help_text=(
        "a string value which specifies the absolute path "
        "of a directory used for bulk importing ``EnkelvoudigInformatieObject``'s. This "
        "value is used to determine the file path for each row in the import metadata "
        "file. By default this is the same directory as the projects directory (``BASE_DIR``)."
    ),
    auto_display_default=False,
    group="Documenten import",
)
IMPORT_DOCUMENTEN_BATCH_SIZE = config(
    "IMPORT_DOCUMENTEN_BATCH_SIZE",
    500,
    help_text=(
        "is the number of rows that will be processed at a time. "
        "Used for bulk importing ``EnkelvoudigInformatieObject``'s."
    ),
    group="Documenten import",
)

NOTIFICATIONS_API_GET_DOMAIN = "openzaak.utils.get_openzaak_domain"
