# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

# Minimal setting to make the logging machinery work correctly
LOGGING_SETTINGS = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {},
    "filters": {
        "failed_notification": {
            "()": "openzaak.notifications.filters.FailedNotificationFilter"
        },
    },
    "handlers": {
        "failed_notification": {
            "level": "DEBUG",
            "filters": ["failed_notification"],
            "class": "openzaak.notifications.handlers.DatabaseLogHandler",
        },
    },
    "loggers": {
        "vng_api_common.notifications.viewsets": {
            "handlers": ["failed_notification"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


class NotificationsConfigMixin:
    @staticmethod
    def _configure_notifications():
        from vng_api_common.notifications.models import NotificationsConfig
        from zgw_consumers.constants import APITypes, AuthTypes
        from zgw_consumers.models import Service

        svc, _ = Service.objects.update_or_create(
            api_root="https://notificaties-api.vng.cloud/api/v1/",
            defaults=dict(
                label="NRC",
                api_type=APITypes.nrc,
                client_id="some-client-id",
                secret="some-secret",
                auth_type=AuthTypes.zgw,
            ),
        )
        config = NotificationsConfig.get_solo()
        config.api_root = svc.api_root
        config.save()
