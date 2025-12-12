# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Callable, Dict, List, NoReturn, Union

from django.db import models, transaction

from cloudevents.exceptions import GenericException
from cloudevents.http import CloudEvent, from_http
from notifications_api_common.tasks import send_notification
from notifications_api_common.viewsets import NotificationMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


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


type CloudEvenHandler = Callable[[CloudEvent], None | NoReturn]


class CloudEventWebhook(APIView):
    """Webhook that handles incoming CloudEvents via POST"""

    handlers: set[CloudEvenHandler] = set()

    @classmethod
    def register_handler[T: CloudEvenHandler](cls, f: T, /) -> T:
        cls.handlers.add(f)
        return f

    def post(self, request: Request):
        try:
            event: CloudEvent = from_http(request.headers, request.body)
        except GenericException as e:
            raise ValidationError(
                {"cloudevent": [str(e)]}, code="malformed-cloudevent"
            ) from e

        errors: list[str] = []
        for handle in self.handlers:
            try:
                handle(event)
            except Exception as e:
                errors.append(str(e))

        if errors:
            return Response(
                {"accepted": False, "event_id": event["id"], "errors": errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"accepted": True, "event_id": event["id"]},
            status=status.HTTP_202_ACCEPTED,
        )
