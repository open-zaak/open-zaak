# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import warnings

from django.utils import timezone

import structlog
from notifications_api_common.models import NotificationsConfig
from requests.exceptions import RequestException

from .models import FailedNotification

notifs_logger = structlog.stdlib.get_logger("notifications_api_common.tasks")


class ResendFailure(Exception):
    pass


def resend_notification(notification: FailedNotification) -> None:
    """
    Resend a failed notification.

    The message is extracted from the failed notification log. If any resends
    fail, they are logged again with the same original logger, making them
    available for future retries.
    """
    warnings.warn("Support for notification resend through admin", DeprecationWarning)

    assert notification.retried_at is None, "Can only resend not-retried notifications"
    config = NotificationsConfig.get_solo()
    client = config.get_client()

    try:
        response = client.post("notificaties", json=notification.message)
        response.raise_for_status()
    except RequestException as error:
        notifs_logger.warning(
            "could_not_deliver_message",
            client_base_url=client.base_url,
            notification_msg=notification.message,
            final_try=True,
            exc_info=True,
        )
        raise ResendFailure from error
    finally:
        notification.retried_at = timezone.now()
        notification.save()
