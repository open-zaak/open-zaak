# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging
import warnings


class FailedNotificationFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "notification_msg") and getattr(record, "final_try", False):
            warnings.warn(
                "Support for FailedNotification logging is deprecated",
                DeprecationWarning,
            )
            return True
        return False
