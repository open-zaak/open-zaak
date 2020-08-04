# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
# Minimal setting to make the logging machinery work correctly
LOGGING_SETTINGS = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {},
    "filters": {
        "failed_notification": {
            "()": "openzaak.notifications.filters.FailedNotificationFilter"
        },
    },
    "handlers": {
        "failed_notification": {
            "level": "DEBUG",
            "filters": ["failed_notification"],
            "class": "openzaak.notifications.handlers.DatabaseLogHandler",
        },
    },
    "loggers": {
        "vng_api_common.notifications.viewsets": {
            "handlers": ["failed_notification"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
