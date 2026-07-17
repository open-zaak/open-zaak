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

    def _get_main_resource_key(
        self, main_resource_keys: dict[str, str] | None, kanaal: Kanaal
    ) -> str:
        """
        Get the main_resource defined for the kanaal label
        Otherwise use the kanaal main resource.

        main_resource_keys are only used for nested fields
        besluitInformatieObject -> besluit -> zaak
        """
        if main_resource_keys and main_resource_keys.get(kanaal.label):
            return main_resource_keys.get(kanaal.label)

        return kanaal.main_resource._meta.model_name

    def _get_nested_main_object_url_from_instance(self, key, instance):
        """Returns the url of an nested FK field"""
        obj = instance
        for field in key.split("."):
            obj = getattr(obj, field, None)
        return obj.get_absolute_api_url(request=self.request) if obj else ""

    def _get_nested_main_object_url_from_dict(self, key, data):
        """Returns a nested url field from a dict"""
        for field in key.split("."):
            if data is None:
                return ""
            data = data.get(field)
        return data if isinstance(data, str) else ""

    def _get_nested_main_object_url(
        self,
        key: str,  # format a.b.c
        nested_main_object_resource: Type[models.Model] | dict | None,
    ):
        """returns the nested url key field from an instance or dict"""
        if isinstance(nested_main_object_resource, dict):
            return self._get_nested_main_object_url_from_dict(
                key, nested_main_object_resource
            )

        if isinstance(nested_main_object_resource, models.Model):
            return self._get_nested_main_object_url_from_instance(
                key, nested_main_object_resource
            )

        return ""

    def _main_object_url_exists(
        self,
        data: dict,
        key: str,
        nested_main_object_resource: Type[models.Model] | dict | None,
    ) -> bool:
        """
        Checks if the main object url exists
        E.g. besluit zaak is not required
        if the main_object_url is not part of the notification data it is fetched from an
        instance or dict and added to the notification data
        """
        if "." not in key:
            # original flow
            url = data.get(key)
        else:
            url = self._get_nested_main_object_url(key, nested_main_object_resource)
            final_key = key.split(".")[-1]
            data[final_key] = url
        return url != ""

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
        main_resource_keys: dict[str, str] | None = None,
        nested_main_object_resource: Type[models.Model] | dict | None = None,
    ):
        if replace_urls_for is None:
            replace_urls_for = []
        replace_urls_for.append("url")

        notification_data = data.copy()
        for kanaal in kanalen:
            if model != kanaal.main_resource and not self._main_object_url_exists(
                notification_data,
                self._get_main_resource_key(main_resource_keys, kanaal),
                nested_main_object_resource,
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
            getattr(self, "notifications_replace_urls_for", None),
            getattr(self, "notifications_main_resource_keys", None),
            data.serializer.instance,
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
                config.get("notifications_replace_urls_for"),
                config.get("notifications_main_resource_keys"),
                data,
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
