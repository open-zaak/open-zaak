import os

os.environ.setdefault("DB_HOST", "db")
os.environ.setdefault("DB_NAME", "postgres")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "")

from .production import *  # noqa isort:skip

#
# Custom settings
#

ENVIRONMENT = "docker"
