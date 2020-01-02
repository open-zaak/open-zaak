import logging


class FailedNotificationFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "notification_msg"):
            return True
        return False
