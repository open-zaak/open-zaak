# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.conf import settings
from django.utils.module_loading import import_string

from drf_spectacular.utils import extend_schema
from notifications_api_common.api.serializers import NotificatieSerializer
from notifications_api_common.constants import SCOPE_NOTIFICATIES_PUBLICEREN_LABEL
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from vng_api_common.permissions import AuthScopesRequired
from vng_api_common.scopes import Scope
from vng_api_common.serializers import FoutSerializer, ValidatieFoutSerializer


class NotificationBaseView(APIView):
    schema = None
    permission_classes = (AuthScopesRequired,)
    required_scopes = Scope(SCOPE_NOTIFICATIES_PUBLICEREN_LABEL, private=True)

    def get_serializer(self, *args, **kwargs):
        return NotificatieSerializer(*args, **kwargs)

    @extend_schema(
        responses={
            204: "",
            400: ValidatieFoutSerializer,
            401: FoutSerializer,
            403: FoutSerializer,
            429: FoutSerializer,
            500: FoutSerializer,
            502: FoutSerializer,
            503: FoutSerializer,
        },
        operation_id="notification_receive",
        tags=["Notificaties"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.handle_notification(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def handle_notification(self, message):
        raise NotImplementedError("Subclasses must implement `handle_notification`.")


class NotificationView(NotificationBaseView):
    def handle_notification(self, message: dict) -> None:
        handler_path = getattr(
            settings,
            "ZAAK_NOTIFICATIONS_HANDLER",
            "openzaak.components.zaken.notifications.handlers.default",
        )
        handler = import_string(handler_path)
        handler.handle(message)
