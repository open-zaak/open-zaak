import os

import django.db.models.options as options
from django.urls import reverse_lazy

import raven

from .api import *  # noqa
from .plugins import PLUGIN_INSTALLED_APPS

SITE_ID = int(os.getenv("SITE_ID", 1))

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir)
)
BASE_DIR = os.path.abspath(
    os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir)
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("DB_NAME", "openzaak"),
        "USER": os.getenv("DB_USER", "openzaak"),
        "PASSWORD": os.getenv("DB_PASSWORD", "openzaak"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", 5432),
    }
}

# Application definition

INSTALLED_APPS = [
    # Note: contenttypes should be first, see Django ticket #10827
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    # Note: If enabled, at least one Site object is required
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Optional applications.
    "django.contrib.admin",
    "django.contrib.gis",
    # 'django.contrib.admindocs',
    # 'django.contrib.humanize',
    # External applications.
    "axes",
    "django_filters",
    "corsheaders",
    "vng_api_common",  # before drf_yasg to override the management command
    "vng_api_common.authorizations",
    "vng_api_common.audittrails",
    "vng_api_common.notifications",
    "drf_yasg",
    "rest_framework",
    "rest_framework_gis",
    "django_markup",
    "solo",
    "privates",
    "django_better_admin_arrayfield.apps.DjangoBetterAdminArrayfieldConfig",
    # Project applications.
    'openzaak',
    'openzaak.accounts',
    'openzaak.utils',
    'openzaak.components.authorizations',
    'openzaak.components.zaken',
    'openzaak.components.besluiten',
    'openzaak.components.documenten',
    'openzaak.components.catalogi',

] + PLUGIN_INSTALLED_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "openzaak.utils.middleware.LogHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'openzaak.utils.middleware.AuthMiddleware',
    # 'vng_api_common.middleware.AuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'vng_api_common.middleware.APIVersionHeaderMiddleware',
]

ROOT_URLCONF = "openzaak.urls"

# List of callables that know how to import templates from various sources.
RAW_TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
    # 'admin_tools.template_loaders.Loader',
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(DJANGO_PROJECT_DIR, "templates")],
        "APP_DIRS": False,  # conflicts with explicity specifying the loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "openzaak.utils.context_processors.settings",
            ],
            "loaders": RAW_TEMPLATE_LOADERS,
        },
    }
]

WSGI_APPLICATION = "openzaak.wsgi.application"

# Database: Defined in target specific settings files.
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "nl-nl"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

# Translations
LOCALE_PATHS = (os.path.join(DJANGO_PROJECT_DIR, "conf", "locale"),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Additional locations of static files
STATICFILES_DIRS = (os.path.join(DJANGO_PROJECT_DIR, "static"),)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
]

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

MEDIA_URL = "/media/"

FIXTURE_DIRS = (os.path.join(DJANGO_PROJECT_DIR, "fixtures"),)

DEFAULT_FROM_EMAIL = "openzaak@example.com"
EMAIL_TIMEOUT = 10

LOGGING_DIR = os.path.join(BASE_DIR, "log")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {"format": "%(asctime)s %(process)d | %(thread)d | %(message)s"},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "django.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "openzaak.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "performance.log"),
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "requests": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "requests.log"),
            "formatter": "timestamped",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
    },
    "loggers": {
        "openzaak": {"handlers": ["project"], "level": "INFO", "propagate": True},
        "openzaak.utils.middleware": {
            "handlers": ["requests"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {"handlers": ["django"], "level": "ERROR", "propagate": True},
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

#
# Additional Django settings
#

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    "openzaak.accounts.backends.UserModelEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

SESSION_COOKIE_NAME = "openzaak_sessionid"

#
# Silenced checks
#
SILENCED_SYSTEM_CHECKS = ["rest_framework.W001"]

#
# Custom settings
#
PROJECT_NAME = "Open zaak"
SITE_TITLE = "Open zaak"

ENVIRONMENT = None
SHOW_ALERT = True

#
# Library settings
#

# Django-axes
AXES_LOGIN_FAILURE_LIMIT = 30  # Default: 3
AXES_LOCK_OUT_AT_FAILURE = True  # Default: True
AXES_USE_USER_AGENT = False  # Default: False
AXES_COOLOFF_TIME = 1  # One hour
AXES_BEHIND_REVERSE_PROXY = (
    True
)  # Default: False (we are typically using Nginx as reverse proxy)
AXES_ONLY_USER_FAILURES = (
    False
)  # Default: False (you might want to block on username rather than IP)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = (
    False
)  # Default: False (you might want to block on username and IP)


HIJACK_LOGIN_REDIRECT_URL = "/"
HIJACK_LOGOUT_REDIRECT_URL = reverse_lazy("admin:accounts_user_changelist")
HIJACK_REGISTER_ADMIN = False
# This is a CSRF-security risk.
# See: http://django-hijack.readthedocs.io/en/latest/configuration/#allowing-get-method-for-hijack-views
HIJACK_ALLOW_GET_REQUESTS = True

# Django-CORS-middleware
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    "x-requested-with",
    "content-type",
    "accept",
    "origin",
    "authorization",
    "x-csrftoken",
    "user-agent",
    "accept-encoding",
    "accept-crs",
    "content-crs",
)

# Raven
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    INSTALLED_APPS = INSTALLED_APPS + ["raven.contrib.django.raven_compat"]

    if "GIT_SHA" in os.environ:
        GIT_SHA = os.getenv("GIT_SHA")
    else:
        GIT_SHA = raven.fetch_git_sha(BASE_DIR)

    RAVEN_CONFIG = {"dsn": SENTRY_DSN, "release": GIT_SHA}
    LOGGING["handlers"].update(
        {
            "sentry": {
                "level": "WARNING",
                "class": "raven.handlers.logging.SentryHandler",
                "dsn": RAVEN_CONFIG["dsn"],
            }
        }
    )

#
# SSL or not?
#
IS_HTTPS = os.getenv("IS_HTTPS", "1").lower() in ["true", "1", "yes"]

# catalogi settings
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    "mnemonic",
    "filter_fields",
    "ordering_fields",
    "search_fields",
)

# documenten settings
# settings for private media files
PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, "private-media")
PRIVATE_MEDIA_URL = "/private-media/"
SENDFILE_BACKEND = "sendfile.backends.simple"
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = PRIVATE_MEDIA_URL

# settings for uploading large files
MIN_UPLOAD_SIZE = int(os.getenv("MIN_UPLOAD_SIZE", 4 * 2 ** 30))

# urls for OAS3 specifications
SPEC_URL = {
    'zaken': os.path.join(BASE_DIR, 'src/openzaak/components/zaken/openapi.yaml'),
    'besluiten': os.path.join(BASE_DIR, 'src/openzaak/components/besluiten/openapi.yaml'),
    'documenten': os.path.join(BASE_DIR, 'src/openzaak/components/documenten/openapi.yaml'),
    'catalogi': os.path.join(BASE_DIR, 'src/openzaak/components/catalogi/openapi.yaml'),
    'authorizations': os.path.join(BASE_DIR, 'src/openzaak/components/authorizations/openapi.yaml'),
}

# for generate_schema depending on the component
subpath = os.getenv("SUBPATH")
if subpath:
    if not subpath.startswith("/"):
        subpath = f"/{subpath}"
    FORCE_SCRIPT_NAME = subpath
