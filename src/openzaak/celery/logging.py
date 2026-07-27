# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import logging  # noqa: TID251 - correct use to replace stdlib logging
import logging.config  # noqa: TID251 - correct use to replace stdlib logging

from django.conf import settings

import structlog


def receiver_setup_logging(
    loglevel, logfile, format, colorize, **kwargs
):  # pragma: no cover
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        structlog.stdlib.PositionalArgumentsFormatter(),
                    ],
                },
                "plain_console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(),
                    "foreign_pre_chain": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        structlog.stdlib.PositionalArgumentsFormatter(),
                    ],
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": settings.LOG_FORMAT_CONSOLE,
                },
            },
            "loggers": {
                "root": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
                "openzaak": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
                "django_structlog": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
                "maykin_common": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
            },
        }
    )

    exception_processors = (
        [structlog.processors.format_exc_info]
        if settings.LOG_FORMAT_CONSOLE == "json"
        else []
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            *exception_processors,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
