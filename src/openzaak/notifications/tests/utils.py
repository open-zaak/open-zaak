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
        "notifications_api_common.viewsets": {
            "handlers": ["failed_notification"],
            "level": "WARNING",
            "propagate": False,
        },
        "vng_api_common.exception_handling": {
            "handlers": [],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}


class NotificationsConfigMixin:
    @staticmethod
    def _configure_notifications(api_root=None):
        from notifications_api_common.models import NotificationsConfig
        from zgw_consumers.constants import APITypes, AuthTypes
        from zgw_consumers.models import Service

        svc, _ = Service.objects.update_or_create(
            api_root=api_root or "https://notificaties-api.vng.cloud/api/v1/",
            defaults=dict(
                label="NRC",
                api_type=APITypes.nrc,
                client_id="some-client-id",
                secret="some-secret",
                auth_type=AuthTypes.zgw,
            ),
        )
        config = NotificationsConfig.get_solo()
        config.notifications_api_service = svc
        config.save()


def get_notifications_api_root() -> str:
    from notifications_api_common.models import NotificationsConfig

    return NotificationsConfig.get_solo().notifications_api_service.api_root
