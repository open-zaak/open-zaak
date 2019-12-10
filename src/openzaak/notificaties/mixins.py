import logging
from io import StringIO

from .models import FailedNotification


class FailedNotificationFilter(logging.Filter):
    def filter(self, record):
        if record.levelname == "WARNING":
            return True
        return False


class FailedNotificationMixin:
    def notify(self, status_code, data, instance=None):
        stream = StringIO()
        console = logging.StreamHandler(stream=stream)
        logger = logging.getLogger("vng_api_common.notifications.viewsets")
        logger.addHandler(console)

        logger.addFilter(FailedNotificationFilter())

        super().notify(status_code, data, instance=instance)

        logs = stream.getvalue()

        if logs:
            app_name = self.queryset.model._meta.app_label
            model_name = self.queryset.model.__name__

            serialized_instance = None
            if instance:
                serialized = self.serializer_class(
                    instance, context={"request": self.request}
                )
                serialized_instance = serialized.data

            split_logs = logs.split("\n")
            FailedNotification.objects.create(
                app=app_name,
                model=model_name,
                status_code=status_code,
                data=data,
                instance=serialized_instance,
                exception=f"{split_logs[0]} {split_logs[-2]}",
            )
