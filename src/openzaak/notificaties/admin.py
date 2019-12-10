from django.contrib import admin

from .models import FailedNotification


@admin.register(FailedNotification)
class FailedNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "app",
        "model",
        "status_code",
        "exception",
    )
    readonly_fields = ("app", "model", "status_code", "data", "instance", "exception")
