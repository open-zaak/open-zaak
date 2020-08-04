# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging

from django.utils import timezone

from vng_api_common.notifications.models import NotificationsConfig
from zds_client import ClientError

from .models import FailedNotification

notifs_logger = logging.getLogger("vng_api_common.notifications.viewsets")


class ResendFailure(Exception):
    pass


def resend_notification(notification: FailedNotification) -> None:
    """
    Resend a failed notification.

    The message is extracted from the failed notification log. If any resends
    fail, they are logged again with the same original logger, making them
    available for future retries.
    """
    assert notification.retried_at is None, "Can only resend not-retried notifications"
    config = NotificationsConfig.get_solo()
    client = config.get_client()

    try:
        client.create("notificaties", notification.message)
    except ClientError as error:
        notifs_logger.warning(
            "Could not deliver message to %s",
            client.base_url,
            exc_info=True,
            extra={
                "notification_msg": notification.message,
                "status_code": notification.status_code,
            },
        )
        raise ResendFailure from error
    finally:
        notification.retried_at = timezone.now()
        notification.save()
