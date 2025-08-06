# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import transaction

from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import NotificationMixin


class MultipleNotificationMixin(NotificationMixin):
    notification_fields: dict[str, dict[str, str]]

    def _message(self, data, instance=None):
        for field, config in self.notification_fields.items():
            field_data = data[field]
            notifications = field_data if isinstance(field_data, list) else [field_data]

            for notif in notifications:
                # build the content of the notification
                message = self.construct_message(
                    notif,
                    instance=instance,
                    kanaal=config["notifications_kanaal"],
                    model=config["model"],
                    action=config.get("action"),
                )

                transaction.on_commit(lambda msg=message: send_notification.delay(msg))
