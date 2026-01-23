# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import os

import sentry_sdk
from celery.schedules import crontab
from notifications_api_common.settings import *  # noqa

os.environ["_USE_STRUCTLOG"] = "True"

from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config, get_sentry_integrations

from openzaak.components.documenten.constants import DocumentenBackendTypes
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
        "maykin_common",
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
        "vng_api_common.notes",
        "rest_framework_gis",
        "sniplates",  # TODO can this be removed?
        "django_better_admin_arrayfield",  # TODO can this be removed?
        "django_loose_fk",
        "django_celery_beat",
        "capture_tag",
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
    "csp.middleware.CSPMiddleware",
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

# Django-Admin-Index
ADMIN_INDEX_DISPLAY_DROP_DOWN_MENU_CONDITION_FUNCTION = (
    "maykin_common.django_two_factor_auth.should_display_dropdown_menu"
)

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


# Default (connection timeout, read timeout) for the requests library (in seconds)
REQUESTS_DEFAULT_TIMEOUT = (10, 30)

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
CONTENT_SECURITY_POLICY["EXCLUDE_URL_PREFIXES"] = [
    # avoids nonce issues with Redoc
    "/zaken/api/v1/schema",
    "/besluiten/api/v1/schema",
    "/documenten/api/v1/schema",
    "/catalogi/api/v1/schema",
    "/autorisaties/api/v1/schema",
]

CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"] += [
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
]
CONTENT_SECURITY_POLICY["DIRECTIVES"]["img-src"] += [
    "cdnjs.cloudflare.com",
    "tile.openstreetmap.org",
]
CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"] += [
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
]


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

ENABLE_CLOUD_EVENTS = config(
    "ENABLE_CLOUD_EVENTS",
    default=False,
    add_to_docs=False,
    cast=bool,
    help_text="**EXPERIMENTAL**: indicates whether or not cloud events should be sent to the configured endpoint for specific operations on Zaak (not ready for use in production)",
)

NOTIFICATIONS_SOURCE = config(
    "NOTIFICATIONS_SOURCE",
    default="",
    add_to_docs=False,
    help_text="**EXPERIMENTAL**: the identifier of this application to use as the source in notifications and cloudevents",
)

#
# SECURITY settings
#
CSRF_FAILURE_VIEW = "maykin_common.views.csrf_failure"

# This setting is used by the csrf_failure view (accounts app).
# You can specify any path that should match the request.path
# Note: the LOGIN_URL Django setting is not used because you could have
# multiple login urls defined.
LOGIN_URLS = [reverse_lazy("admin:login")]

#
# DOCUMENTEN API BACKEND CONFIGURATION
#
DOCUMENTEN_API_BACKEND = config(
    "DOCUMENTEN_API_BACKEND",
    default=DocumentenBackendTypes.filesystem,
    help_text=(
        "Indicates which backend should be used for the Documenten API. "
        "**WARNING**: if documents already exist in one of these backends, switching "
        "to another backend does not automatically migrate the files. "
        f"Possible options: {', '.join(f'``{v}``' for v in DocumentenBackendTypes.values)}"
    ),
    group="Documenten API",
)

#
# DOCUMENTEN API AZURE BLOB STORAGE INTEGRATION
#
AZURE_ACCOUNT_NAME = config(
    "AZURE_ACCOUNT_NAME",
    None,
    help_text=("Name of the Azure storage account."),
    group="Documenten API Azure Blob Storage",
)
AZURE_CLIENT_ID = config(
    "AZURE_CLIENT_ID",
    None,
    help_text=("Application (client) ID of the app registered in Azure for Open Zaak."),
    group="Documenten API Azure Blob Storage",
)
AZURE_TENANT_ID = config(
    "AZURE_TENANT_ID",
    None,
    help_text=("Directory (tenant) ID of the Azure AD instance."),
    group="Documenten API Azure Blob Storage",
)
AZURE_CLIENT_SECRET = config(
    "AZURE_CLIENT_SECRET",
    None,
    help_text=("Client secret of the app registered in Azure for Open Zaak."),
    group="Documenten API Azure Blob Storage",
)
AZURE_CONTAINER = config(
    "AZURE_CONTAINER",
    "openzaak",
    help_text=(
        "Name of the Azure blob storage container where the content of Documenten will be stored. "
        "This container must already exist in Azure. "
        "**WARNING**: changing this name after documents have already been created "
        "in the old container requires manual migration of those documents."
    ),
    group="Documenten API Azure Blob Storage",
)
AZURE_LOCATION = config(
    "AZURE_LOCATION",
    "documenten",
    help_text=(
        "Location where the uploaded Documenten content will be stored. "
        "**WARNING**: changing this location after documents have already been created "
        "at the old location requires manual migration of those documents."
    ),
    group="Documenten API Azure Blob Storage",
)
AZURE_CONNECTION_TIMEOUT_SECS = config(
    "AZURE_CONNECTION_TIMEOUT_SECS",
    5,
    help_text=(
        "Number of seconds before a timeout will be raised when making requests to "
        "Azure."
    ),
    group="Documenten API Azure Blob Storage",
)
AZURE_STORAGE_API_VERSION = config(
    "AZURE_STORAGE_API_VERSION",
    "",
    help_text=(
        "The Storage API version to use for requests. Default value is the most recent "
        "service version that is compatible with the current SDK. Setting to an older "
        "version may result in reduced feature compatibility. "
        "See https://learn.microsoft.com/en-us/rest/api/storageservices/versioning-for-the-azure-storage-services "
        "for more information."
    ),
    auto_display_default=False,
    group="Documenten API Azure Blob Storage",
)

if AZURE_STORAGE_API_VERSION:
    # Only override the version if it's explicitly set, that way we can rely on the
    # default version specified by the azure-sdk if it's not explicitly set
    AZURE_CLIENT_OPTIONS = {"api_version": AZURE_STORAGE_API_VERSION}

AZURE_URL_EXPIRATION_SECS = config(
    "AZURE_URL_EXPIRATION_SECS",
    60,
    help_text=(
        "Seconds before a URL to a blob expires, set to ``None`` to never expire it. "
        "Be aware the container must have public read permissions in order to access "
        "a URL without expiration date."
    ),
    group="Documenten API Azure Blob Storage",
)


#
# DOCUMENTEN API S3 STORAGE INTEGRATION
#
# Authentication Settings
AWS_S3_SESSION_PROFILE = config(
    "S3_SESSION_PROFILE",
    None,
    help_text=(
        "Name of the S3 CLI profile to use for authentication when connecting to S3 strorage."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_ACCESS_KEY_ID = config(
    "S3_ACCESS_KEY_ID",
    None,
    help_text=("Access key ID used to authenticate with S3 storage."),
    group="Documenten API S3 Storage",
)
AWS_S3_SECRET_ACCESS_KEY = config(
    "S3_SECRET_ACCESS_KEY",
    None,
    help_text=(
        "Secret access key used together with S3_ACCESS_KEY_ID to authenticate to S3 storage."
    ),
    group="Documenten API S3 Storage",
)
AWS_SESSION_TOKEN = config(
    "S3_SESSION_TOKEN",
    None,
    help_text=("Session token used for temporary S3 credentials."),
    group="Documenten API S3 Storage",
)

# General Settings
AWS_STORAGE_BUCKET_NAME = config(
    "S3_STORAGE_BUCKET_NAME",
    "openzaak",
    help_text=(
        "The name of the S3 bucket that will host the files."
        " Note: the bucket must exist already, because Open Zaak will not create it automatically."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_OBJECT_PARAMETERS = config(
    "S3_OBJECT_PARAMETERS",
    {},
    help_text=(
        "Use this to set parameters on all objects. To set these on a per-object basis,"
        "subclass the backend and override S3Storage.get_object_parameters."
    ),
    group="Documenten API S3 Storage",
)
AWS_DEFAULT_ACL = config(
    "S3_DEFAULT_ACL",
    None,
    help_text=(
        "Use this to set an ACL on your file such as public-read. If not set the file will be private per Amazon’s default."
        "If the ACL parameter is set in object_parameters, then this setting is ignored."
    ),
    group="Documenten API S3 Storage",
)
AWS_QUERYSTRING_AUTH = config(
    "S3_QUERYSTRING_AUTH",
    True,
    help_text=(
        "Setting S3_QUERYSTRING_AUTH to False to remove query parameter authentication from generated URLs."
        "This can be useful if your S3 buckets are public."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_MAX_MEMORY_SIZE = config(
    "S3_MAX_MEMORY_SIZE",
    0,
    help_text=(
        "The maximum amount of memory (in bytes) a file can take up before being rolled over into a temporary file on disk."
    ),
    group="Documenten API S3 Storage",
)
AWS_QUERYSTRING_EXPIRE = config(
    "S3_QUERYSTRING_EXPIRE",
    3600,
    help_text=("The number of seconds that a generated URL is valid for."),
    group="Documenten API S3 Storage",
)
AWS_S3_URL_PROTOCOL = config(
    "S3_URL_PROTOCOL",
    "https:",
    help_text=(
        "The protocol to use when constructing a custom domain, custom_domain must be True for this to have any effect."
        "Must end in a `:`"
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_FILE_OVERWRITE = config(
    "S3_FILE_OVERWRITE",
    True,
    help_text=(
        "By default files with the same name will overwrite each other. Set this to False to have extra characters appended."
    ),
    group="Documenten API S3 Storage",
)
AWS_LOCATION = config(
    "S3_LOCATION",
    "documenten/",
    help_text=("A path prefix that will be prepended to all uploads."),
    group="Documenten API S3 Storage",
)
AWS_IS_GZIPPED = config(
    "S3_IS_GZIPPED",
    False,
    help_text=(
        "Whether or not to enable gzipping of content types specified by gzip_content_types."
    ),
    group="Documenten API S3 Storage",
)
GZIP_CONTENT_TYPES = config(
    "S3_GZIP_CONTENT_TYPES",
    "(text/css,text/javascript,application/javascript,application/x-javascript,image/svg+xml)",
    help_text=("The list of content types to be gzipped when gzip is True."),
    group="Documenten API S3 Storage",
)
AWS_S3_REGION_NAME = config(
    "S3_REGION_NAME",
    None,
    help_text=("Name of the S3 storage region to use (eg. eu-west-1)"),
    group="Documenten API S3 Storage",
)
AWS_S3_USE_SSL = config(
    "S3_USE_SSL",
    True,
    help_text=(
        "Whether or not to use SSL when connecting to S3, this is passed to the boto3 session resource constructor."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_VERIFY = config(
    "S3_VERIFY",
    None,
    help_text=(
        "Whether or not to verify the connection to S3. Can be set to False to not verify certificates or a path to a CA cert bundle."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_ENDPOINT_URL = config(
    "S3_ENDPOINT_URL",
    None,
    help_text=(
        "Custom S3 URL to use when connecting to S3, including scheme. Overrides region_name and use_ssl."
        "To avoid AuthorizationQueryParametersError errors, region_name should also be set."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_ADDRESSING_STYLE = config(
    "S3_ADDRESSING_STYLE",
    None,
    help_text=("Possible values `virtual` and `path`."),
    group="Documenten API S3 Storage",
)
AWS_S3_PROXIES = config(
    "S3_PROXIES",
    None,
    help_text=("Dictionary of proxy servers to use by protocol or endpoint."),
    group="Documenten API S3 Storage",
)
AWS_S3_TRANSFER_CONFIG = config(
    "S3_TRANSFER_CONFIG",
    None,
    help_text=(
        "Set this to customize the transfer config options such as disabling threads for gevent compatibility;"
        "See the Boto3 docs for TransferConfig for more info."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_CUSTOM_DOMAIN = config(
    "S3_CUSTOM_DOMAIN",
    None,
    help_text=("Set this to specify a custom domain for constructed URLs."),
    group="Documenten API S3 Storage",
)
AWS_CLOUDFRONT_KEY = config(
    "S3_CLOUDFRONT_KEY",
    None,
    help_text=(
        "A private PEM encoded key to use in a boto3 CloudFrontSigner; See CloudFront Signed URLs for more info."
    ),
    group="Documenten API S3 Storage",
)
AWS_CLOUDFRONT_KEY_ID = config(
    "S3_CLOUDFRONT_KEY_ID",
    None,
    help_text=(
        "The S3 key ID for the private key provided with cloudfront_key / S3_CLOUDFRONT_KEY;"
        "See CloudFront Signed URLs for more info."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_SIGNATURE_VERSION = config(
    "S3_SIGNATURE_VERSION",
    None,
    help_text=(
        "The default signature version is s3v4. Set this to s3 to use the legacy signing scheme (aka v2)."
        "Note that only certain regions support that version."
        "You can check to see if your region is one of them in the S3 region list."
    ),
    group="Documenten API S3 Storage",
)
AWS_S3_CLIENT_CONFIG = config(
    "S3_CLIENT_CONFIG",
    None,
    help_text=(
        "An instance of botocore.config.Config to do advanced configuration of the client such as max_pool_connections."
        "See all options in the Botocore docs."
    ),
    group="Documenten API S3 Storage",
)
