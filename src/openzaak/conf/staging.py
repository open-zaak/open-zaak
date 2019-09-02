"""
Staging environment settings module.

This *should* be nearly identical to production.
"""

from .production import *  # noqa

# Show active environment in admin.
ENVIRONMENT = "staging"
