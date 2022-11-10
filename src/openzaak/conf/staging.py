# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Staging environment settings module.

This *should* be nearly identical to production.
"""
import os

os.environ.setdefault("ENVIRONMENT", "staging")

from .production import *  # noqa
