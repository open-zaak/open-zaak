# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os

os.environ.setdefault("DB_HOST", "db")
os.environ.setdefault("DB_NAME", "openzaak")
os.environ.setdefault("DB_USER", "openzaak")
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("DB_CONN_MAX_AGE", "60")

os.environ.setdefault("ENVIRONMENT", "docker")
os.environ.setdefault("LOG_STDOUT", "yes")
os.environ.setdefault("LOG_FORMAT_CONSOLE", "json")

from .production import *  # noqa isort:skip
