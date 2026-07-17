# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Callable, Dict, List, NotRequired, Type, TypedDict, Union

from django.db import models, transaction

import structlog
from cloudevents.exceptions import GenericException
from cloudevents.http import CloudEvent, from_http
from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import (
    NotificationCreateMixin,
    NotificationDestroyMixin,
    NotificationMixin,
    NotificationUpdateMixin,
)
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from structlog.contextvars import bind_contextvars, bound_contextvars
from vng_api_common.constants import ComponentTypes

from openzaak.utils.permissions import AuthScopesRequired

from .kanaal import Kanaal
from .scopes import SCOPE_CLOUDEVENTS_BEZORGEN

logger = structlog.stdlib.get_logger(__name__)


def _schedule(message: dict):
    transaction.on_commit(lambda msg=message: send_notification.delay(msg))


class NotificationFieldConfig(TypedDict):
    notifications_kanaal: Kanaal
    model: Type[models.Model]
    action: str | None


class MultipleChannelNotificationFieldConfig(TypedDict):
    notifications_kanalen: list[Kanaal]
    model: Type[models.Model]
    action: NotRequired[str]
    replace_urls_for: NotRequired[list[str]]


class MultipleObjectsNotificationMixin(NotificationMixin):
    """
    NotificationMixin that adds support for sending notification per object in convenience endpoints.
    """

    notification_fields: dict[str, NotificationFieldConfig]

    def _iter_field_notifications(
        self,
        data: dict,
        notification_fields: dict[
            str, NotificationFieldConfig | MultipleChannelNotificationFieldConfig
        ],
    ):
        for field, config in notification_fields.items():
            field_data = data[field]
            notifications = field_data if isinstance(field_data, list) else [field_data]
            for notification in notifications:
                yield config, notification

    def notify(
        self,
        status_code: int,
        data: Union[List, Dict],
        instance: models.Model | None = None,
        **kwargs,
    ) -> None:
        # TODO add comment why this is needed
        super().notify(status_code, data, instance)

    def _message(self, data, instance=None):
        for config, notification in self._iter_field_notifications(
            data, self.notification_fields
        ):
            message = self.construct_message(
                notification,
                instance=instance,
                kanaal=config["notifications_kanaal"],
                model=config["model"],
                action=config.get("action"),
            )

            _schedule(message)


class MultipleChannelNotificationMixin(NotificationMixin):
    """
    NotificationMixin that adds support for sending notifications over multiple channels in deprecated APIS.
    """

    notifications_kanalen: list[Kanaal]
    notifications_main_resource_keys: dict[str, str]  # kanaal label, main_resource_key
    replace_urls_for: list[str]

    def get_main_resource_key(self, kanaal: Kanaal):
        if hasattr(
            self, "notifications_main_resource_keys"
        ) and self.notifications_main_resource_keys.get(kanaal.label):
            return self.notifications_main_resource_keys.get(kanaal.label)

        return kanaal.main_resource._meta.model_name

    def get_notification_main_object_url(self, data: dict, kanaal: Kanaal) -> str:
        """
        Retrieve the URL for the main object.
        """

        key = self.get_main_resource_key(kanaal)

        if "." not in key:
            # original flow
            return data[key]

        obj = data.serializer.instance
        for field in key.split("."):
            obj = getattr(obj, field, None)
        return obj.get_absolute_api_url(request=self.request) if obj else ""

    def _replace_namespace(self, url: str, namespace: str) -> str:
        prefix, sep, rest = url.partition("/api")
        if not sep:
            return url

        base, _, old_namespace = prefix.rpartition("/")
        return f"{base}/{namespace}{sep}{rest}"

    def _iter_kanalen(
        self,
        data: dict,
        model: models.Model,
        kanalen: list[Kanaal],
        replace_urls_for: list[str] | None = None,
    ):
        if replace_urls_for is None:
            replace_urls_for = []
        replace_urls_for.append("url")

        notification_data = data.copy()
        for kanaal in kanalen:
            # Do not send notification if kanaal main object does not exist on the instance
            # E.g. besluit zaak is not required
            if (
                model != kanaal.main_resource
                and self.get_notification_main_object_url(notification_data, kanaal)
                == ""
            ):
                continue

            for field in replace_urls_for:
                notification_data[field] = self._replace_namespace(
                    notification_data[field], kanaal.label
                )

            yield kanaal, notification_data

    def _message(self, data, instance=None):
        for kanaal, notification_data in self._iter_kanalen(
            data,
            self.get_queryset().model,
            self.notifications_kanalen,
            getattr(self, "replace_urls_for", None),
        ):
            message = self.construct_message(
                notification_data, instance=instance, kanaal=kanaal
            )
            _schedule(message)


class MultipleChannelNotificationViewSetMixin(
    MultipleChannelNotificationMixin,
    NotificationCreateMixin,
    NotificationUpdateMixin,
    NotificationDestroyMixin,
):
    pass


class MultipleChannelNotificationCreateMixin(
    MultipleChannelNotificationMixin,
    NotificationCreateMixin,
):
    pass


class MultipleChannelNotificationDestroyMixin(
    MultipleChannelNotificationMixin,
    NotificationDestroyMixin,
):
    pass


class MultipleObjectsMultipleChannelNotificationMixin(
    MultipleChannelNotificationMixin, MultipleObjectsNotificationMixin
):
    notification_fields: dict[str, MultipleChannelNotificationFieldConfig]

    def _message(self, data, instance=None):
        for config, notification in self._iter_field_notifications(
            data, self.notification_fields
        ):
            for kanaal, notification_data in self._iter_kanalen(
                notification,
                config["model"],
                config["notifications_kanalen"],
                config.get("replace_urls_for"),
            ):
                message = self.construct_message(
                    notification_data,
                    instance=instance,
                    kanaal=kanaal,
                    model=config["model"],
                    action=config.get("action"),
                )
                _schedule(message)


type CloudEventHandler = Callable[[CloudEvent], None]


class CloudEventWebhook(APIView):
    """Webhook that handles incoming CloudEvents via POST"""

    required_scopes = {"post": SCOPE_CLOUDEVENTS_BEZORGEN}
    component = ComponentTypes.nrc
    permission_classes = [AuthScopesRequired]

    handlers: set[CloudEventHandler] = set()

    @classmethod
    def register_handler[T: CloudEventHandler](cls, f: T, /) -> T:
        """Register a handler for incoming cloud events.

        Handlers should log exceptions (with appropriate log level) if it doesn't
        make sense to retry the exact same event.

        Any uncaught exceptions are considered runtime errors, and will be
        signalled to the event provider as such, so it can retry the event at a
        later time.
        """
        cls.handlers.add(f)
        return f

    def post(self, request: Request):
        if request.headers.get("content-type") != "application/cloudevents+json":
            # this is not checked by from_http
            return Response(status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        try:
            event: CloudEvent = from_http(request.headers, request.body)
        except GenericException as e:
            raise ValidationError(
                {"cloudevent": [str(e)]}, code="malformed-cloudevent"
            ) from e

        bind_contextvars(cloud_event=event)

        errors = False
        for handle in self.handlers:
            try:
                with bound_contextvars(handler=handle):
                    handle(event)
            except Exception:
                logger.exception("incoming_cloud_event_uncaught_exception")
                errors = True

        if errors:
            return Response(
                {
                    "accepted": False,
                    "event_id": event["id"],
                    "code": "incoming_cloud_event_uncaught_exception",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"accepted": True, "event_id": event["id"]},
            status=status.HTTP_202_ACCEPTED,
        )
