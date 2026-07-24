# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

# Minimal setting to make the logging machinery work correctly
LOGGING_SETTINGS = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {},
    "filters": {},
    "handlers": {},
    "loggers": {
        "vng_api_common.exception_handling": {
            "handlers": [],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}
