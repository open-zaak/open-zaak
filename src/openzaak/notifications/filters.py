# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging


class FailedNotificationFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "notification_msg") and hasattr(record, "status_code"):
            return True
        return False
