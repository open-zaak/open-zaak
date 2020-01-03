import logging


class FailedNotificationFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "notification_msg") and hasattr(record, "status_code"):
            return True
        return False
