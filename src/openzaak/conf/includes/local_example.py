# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import sys

from ..dev import DATABASES, INSTALLED_APPS

INSTALLED_APPS += ["django_extensions"]


if "test" in sys.argv:
    # Runs the tests on PostgreSQL cluster tweaked for performance
    DATABASES["default"].update({"USER": "postgres", "PORT": 5433})

    # Speed up tests by reducing time spend password hashing
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
