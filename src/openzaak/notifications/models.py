# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_db_logger.models import StatusLog


class FailedNotification(StatusLog):
    """
    Track extra metadata about failed notifications.

    We subclass with multi-table inheritance to tie it to the original log
    record, but attach extra information about the failed notification so we
    can easily resend them from the admin interface.
    """

    status_code = models.IntegerField(
        _("status_code"),
        help_text=_("Status code received from the Notifications API."),
    )
    message = JSONField(
        _("notification message"),
        help_text=_("Content of the notification that was attempted to send."),
    )
    retried_at = models.DateTimeField(
        _("retried at"),
        null=True,
        editable=False,
        help_text=_("Timestamp logging if/when this message was retried."),
    )

    class Meta:
        verbose_name = _("failed notification")
        verbose_name_plural = _("failed notifications")

    @property
    def retried(self) -> bool:
        return self.retried_at is not None
