# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Callable, Dict, List, Union

from django.db import models, transaction

import structlog
from cloudevents.exceptions import GenericException
from cloudevents.http import CloudEvent, from_http
from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import NotificationMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from structlog.contextvars import bind_contextvars, bound_contextvars
from vng_api_common.constants import ComponentTypes

from openzaak.utils.permissions import AuthScopesRequired

from .scopes import SCOPE_CLOUDEVENTS_BEZORGEN

logger = structlog.stdlib.get_logger(__name__)


class MultipleNotificationMixin(NotificationMixin):
    notification_fields: dict[str, dict[str, str]]

    def notify(
        self,
        status_code: int,
        data: Union[List, Dict],
        instance: models.Model = None,
        **kwargs,
    ) -> None:
        super().notify(status_code, data, instance)

    def _message(self, data, instance=None):
        for field, config in self.notification_fields.items():
            field_data = data[field]
            notifications = field_data if isinstance(field_data, list) else [field_data]

            for notif in notifications:
                # build the content of the notification
                message = self.construct_message(
                    notif,
                    instance=instance,
                    kanaal=config["notifications_kanaal"],
                    model=config["model"],
                    action=config.get("action"),
                )

                transaction.on_commit(lambda msg=message: send_notification.delay(msg))


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
