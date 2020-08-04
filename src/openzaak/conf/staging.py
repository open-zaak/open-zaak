# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Staging environment settings module.

This *should* be nearly identical to production.
"""

from .production import *  # noqa

# Show active environment in admin.
ENVIRONMENT = "staging"
