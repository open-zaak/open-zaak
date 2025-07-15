from django.db import transaction

from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import NotificationMixin


class MultipleNotificationMixin(NotificationMixin):
    notification_fields: dict[str, dict[str, str]]

    def _message(self, data, instance=None):
        for field, config in self.notification_fields.items():
            # build the content of the notification
            message = self.construct_message(
                data[field],
                instance=instance,
                kanaal=config["notifications_kanaal"],
                model=config["model"],
            )

            transaction.on_commit(lambda msg=message: send_notification.delay(msg))
