# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib import admin
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

import structlog

from .models import FailedNotification
from .resend import ResendFailure, resend_notification

logger = structlog.stdlib.get_logger(__name__)


@admin.action(description=_("Resend %(verbose_name_plural)s"))
def resend_notifications(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    for failed in queryset:
        if failed.retried_at is not None:
            logger.info(
                "not_resending_already_resent_notification",
                failed_pk=failed.pk,
            )
            continue

        with transaction.atomic():
            try:
                resend_notification(failed)
            except ResendFailure:
                continue
            except Exception:
                logger.error(
                    "resend_failed",
                    failed_pk=failed.pk,
                    exc_info=True,
                )
                continue


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
