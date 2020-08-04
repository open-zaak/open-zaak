# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging

from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from .models import FailedNotification
from .resend import ResendFailure, resend_notification

logger = logging.getLogger(__name__)


def resend_notifications(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    for failed in queryset:
        if failed.retried_at is not None:
            logger.info("Not resending already re-sent notification %d", failed.pk)
            continue

        with transaction.atomic():
            try:
                resend_notification(failed)
            except ResendFailure:
                continue
            except Exception:
                logger.exception("Resend for %d failed", failed.pk)
                continue


resend_notifications.short_description = _("Resend %(verbose_name_plural)s")


@admin.register(FailedNotification)
class FailedNotificationAdmin(admin.ModelAdmin):
    list_display = ("msg", "kanaal", "aanmaakdatum", "retried_at", "statuslog")
    list_filter = ("retried_at",)
    date_hierarchy = "create_datetime"
    search_fields = ("message__kanaal",)
    actions = [resend_notifications]

    def kanaal(self, obj) -> str:
        return obj.message["kanaal"]

    def aanmaakdatum(self, obj) -> str:
        return obj.message["aanmaakdatum"]

    def statuslog(self, obj) -> str:
        href = reverse(
            "admin:django_db_logger_statuslog_change", args=(obj.statuslog_ptr_id,)
        )
        return format_html('<a href="{href}">Log entry</a>', href=href)
