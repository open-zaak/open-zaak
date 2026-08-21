# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import models

from django_loose_fk.virtual_models import FKHandler
from vng_api_common.constants import CommonResourceAction
from vng_api_common.notifications.handlers import (
    KANAAL_AUTORISATIES,
    AuthHandler as _AuthHandler,
    LoggingHandler,
    RoutingHandler,
)
from vng_api_common.utils import get_uuid_from_path
from zgw_consumers.models import Service

from openzaak.components.autorisaties.api.serializers import ApplicatieUuidSerializer
from openzaak.components.autorisaties.models import Applicatie


class FkServiceHandler(FKHandler):
    def __get__(self, instance, cls=None) -> models.Model:
        raw_data = instance._loose_fk_data.get(self.field_name, None)

        if isinstance(raw_data, Service):
            return raw_data

        return super().__get__(instance, cls)


class AuthHandler(_AuthHandler):
    def handle(self, message: dict) -> None:
        uuid = get_uuid_from_path(message["resource_url"])

        if message["actie"] == CommonResourceAction.destroy:
            Applicatie.objects.filter(uuid=uuid).delete()
            return

        # get info
        applicatie_data = self._request_auth(message["resource_url"])
        applicatie_data["uuid"] = uuid

        # update models
        try:
            applicatie = Applicatie.objects.get(uuid=uuid)
        except Applicatie.DoesNotExist:
            applicatie_serializer = ApplicatieUuidSerializer(data=applicatie_data)
        else:
            applicatie_serializer = ApplicatieUuidSerializer(
                applicatie, data=applicatie_data
            )
        applicatie_serializer.is_valid(raise_exception=True)
        applicatie_serializer.save()


log = LoggingHandler()
auth = AuthHandler()

default = RoutingHandler({KANAAL_AUTORISATIES: auth}, default=log)
