from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import FailedNotification


@admin.register(FailedNotification)
class FailedNotificationAdmin(admin.ModelAdmin):
    list_display = ("msg", "kanaal", "aanmaakdatum", "retried_at", "statuslog")
    list_filter = ("retried_at",)
    date_hierarchy = "create_datetime"
    search_fields = ("message__kanaal",)

    def kanaal(self, obj) -> str:
        return obj.message["kanaal"]

    def aanmaakdatum(self, obj) -> str:
        return obj.message["aanmaakdatum"]

    def statuslog(self, obj) -> str:
        href = reverse(
            "admin:django_db_logger_statuslog_change", args=(obj.statuslog_ptr_id,)
        )
        return format_html('<a href="{href}">Log entry</a>', href=href)
