# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import (
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    NotRequired,
    TypedDict,
    TypeVar,
    Union,
)

from django.conf import settings
from django.db import models, transaction

import structlog
from cloudevents.exceptions import GenericException
from cloudevents.http import CloudEvent, from_http
from notifications_api_common.models import NotificationTypes
from notifications_api_common.tasks import create_failed_notification, send_notification
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

from ..utils.namespacing import (
    get_nested_main_object_url_from_dict,
    get_nested_main_object_url_from_instance,
    replace_namespaces,
)
from .kanaal import Kanaal
from .scopes import SCOPE_CLOUDEVENTS_BEZORGEN

logger = structlog.stdlib.get_logger(__name__)


def _schedule(message: dict) -> None:
    pk = create_failed_notification(message, NotificationTypes.notification)
    transaction.on_commit(
        lambda msg=message, notification_id=pk: send_notification.delay(
            msg, notification_id
        )
    )


class NotificationFieldConfig(TypedDict):
    notifications_kanaal: Kanaal
    model: type[models.Model]
    action_override: NotRequired[str]


class KanaalConfig(TypedDict):
    kanaal: Kanaal
    deprecated: NotRequired[bool]
    namespace: NotRequired[str]  # kanaal.label override


class MultipleChannelNotificationFieldConfig(TypedDict):
    notifications_kanalen: list[KanaalConfig]
    model: type[models.Model]
    action: NotRequired[str]
    notifications_replace_urls_for: NotRequired[list[str]]
    notifications_main_resource_keys: NotRequired[dict[str, str]]


TNotificationFieldConfig = TypeVar(
    "TNotificationFieldConfig",
    NotificationFieldConfig,
    MultipleChannelNotificationFieldConfig,
)


class _MultipleObjectsNotificationMixin(
    Generic[TNotificationFieldConfig], NotificationMixin
):
    notification_fields: dict[str, TNotificationFieldConfig]

    def _iter_field_notifications(
        self,
        data: dict,
        notification_fields: dict[str, TNotificationFieldConfig],
    ) -> Generator[
        tuple[TNotificationFieldConfig, dict],
        None,
        None,
    ]:
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
        """
        ZaakBijwerkenViewset overrides notify to add more parameters, but notify call
        is done in ZaakUpdateActionViewSet which is used by other convenience viewsets.
        For the other ones the kwargs can be ignored but this override allows them.
        """
        super().notify(status_code, data, instance)


class MultipleObjectsNotificationMixin(
    _MultipleObjectsNotificationMixin[NotificationFieldConfig]
):
    """
    NotificationMixin that adds support for sending notification per object in convenience endpoints.
    """

    notification_fields: dict[str, NotificationFieldConfig]

    def _message(self, data, instance=None) -> None:
        for config, notification in self._iter_field_notifications(
            data, self.notification_fields
        ):
            message = self.construct_message(
                notification,
                instance=instance,
                kanaal=config["notifications_kanaal"],
                model=config["model"],
                action=config.get("action_override"),
            )

            _schedule(message)


class MultipleChannelNotificationMixin(NotificationMixin):
    """
    NotificationMixin that adds support for sending notifications over multiple channels in deprecated APIS.
    """

    notifications_kanalen: list[KanaalConfig]

    # kanaal label, main_resource_key
    notifications_main_resource_keys: dict[str, str] | None = None
    notifications_replace_urls_for: list[str] | None = None

    def _get_nested_main_object_url(
        self,
        key: str,  # format a.b.c
        main_object_resource: models.Model | dict,
    ) -> dict[str, str] | None:
        """returns the nested url key field from an instance or dict"""
        url = None
        if isinstance(main_object_resource, dict):
            url = get_nested_main_object_url_from_dict(key, main_object_resource)

        elif isinstance(main_object_resource, models.Model):
            url = get_nested_main_object_url_from_instance(
                key, main_object_resource, self.request
            )

        final_key = key.split(".")[-1]
        return {final_key: url} if url else None

    def _iter_kanalen(
        self,
        data: dict,
        model: type[models.Model],
        kanaal_configs: list[KanaalConfig],
        replace_urls_for: list[str] | None = None,
        main_resource_keys: dict[str, str] | None = None,
        main_object_resource: models.Model | dict | None = None,
    ) -> Generator[tuple[Kanaal, dict], None, None]:
        fields = ["url"] + (replace_urls_for or [])

        for kanaal_config in kanaal_configs:
            if (
                kanaal_config.get("deprecated", False)
                and not settings.SEND_NOTIFICATIONS_ON_DEPRECATED_CHANNELS
            ):
                continue
            kanaal = kanaal_config["kanaal"]
            namespace = kanaal_config.get("namespace", kanaal.label)
            notification_data = replace_namespaces(data, fields, namespace)
            # if model == main_resource the url field is used which is always set
            # if the model is not main_resource it can be port of notification_data or from a related model.
            # No notification should be sent if the main resource is not set (because it's not required on the model).
            if model != kanaal.main_resource:
                if not main_resource_keys or namespace not in main_resource_keys:
                    # original flow
                    url = self.get_notification_main_object_url(
                        notification_data, kanaal
                    )

                    if url == "":
                        # is is possible the main_object_url is empty (zaak is not required on besluit)
                        continue

                else:
                    # main_object is not part of the notification data and needs to be fetched from an instance or dict (main_object_resource)
                    # to make NotificationMixin.construct_message work without too many changes.
                    # the urls is added with its expected key e.g. {zaak: <zaak_url>}

                    assert main_object_resource is not None

                    url_data = self._get_nested_main_object_url(
                        main_resource_keys[namespace],
                        main_object_resource,
                    )
                    if not url_data:
                        # is is possible the main_object_url is empty (zaak is not required on besluit for besluitinformatieobject)
                        continue
                    else:
                        notification_data.update(url_data)

            yield kanaal, notification_data

    def _message(self, data, instance=None) -> None:
        for kanaal, notification_data in self._iter_kanalen(
            data,
            self.get_queryset().model,
            self.notifications_kanalen,
            self.notifications_replace_urls_for,
            self.notifications_main_resource_keys,
            data.serializer.instance,
        ):
            message = self.construct_message(
                notification_data, instance=instance, kanaal=kanaal
            )
            _schedule(message)


class MultipleChannelNotificationCreateMixin(
    MultipleChannelNotificationMixin,
    NotificationCreateMixin,
):
    pass


class MultipleChannelNotificationUpdateMixin(
    MultipleChannelNotificationMixin,
    NotificationUpdateMixin,
):
    pass


class MultipleChannelNotificationDestroyMixin(
    MultipleChannelNotificationMixin,
    NotificationDestroyMixin,
):
    pass


class MultipleChannelNotificationViewSetMixin(
    MultipleChannelNotificationCreateMixin,
    MultipleChannelNotificationUpdateMixin,
    MultipleChannelNotificationDestroyMixin,
):
    pass


class MultipleObjectsMultipleChannelNotificationMixin(
    MultipleChannelNotificationMixin,
    _MultipleObjectsNotificationMixin[MultipleChannelNotificationFieldConfig],
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
