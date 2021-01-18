# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Logging handler to save the log message/notification into the DB.

Implementation inspired on django_db_logger.db_log_handler. Note that filters
run first, and this code assumes that the
:class:`openzaak.notifications.filters.FailedNotificationFilter` was properly
configured for the handler.
"""

import logging
import traceback


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from .models import FailedNotification

        trace = None

        if record.exc_info:
            trace = traceback.format_exc()

        kwargs = {
            "logger_name": record.name,
            "level": record.levelno,
            "msg": record.getMessage(),
            "trace": trace,
            "status_code": record.status_code,
            "message": record.notification_msg,
        }

        FailedNotification.objects.create(**kwargs)
