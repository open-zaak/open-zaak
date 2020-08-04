# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os

os.environ.setdefault("DB_HOST", "db")
os.environ.setdefault("DB_NAME", "postgres")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "")

os.environ.setdefault("LOG_STDOUT", "yes")

from .production import *  # noqa isort:skip

#
# Custom settings
#

ENVIRONMENT = "docker"
