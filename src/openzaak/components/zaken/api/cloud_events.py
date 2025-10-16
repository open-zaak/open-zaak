# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from celery import shared_task
from rest_framework.reverse import reverse
from structlog.stdlib import get_logger
from zgw_consumers.client import build_client

from openzaak.components.zaken.models import Zaak
from openzaak.config.models import CloudEventConfig

logger = get_logger(__name__)

ZAAK_GEOPEND = "nl.overheid.zaken.zaak-geopend"
ZAAK_GEMUTEERD = "nl.overheid.zaken.zaak-gemuteerd"
ZAAK_VERWIJDEREN = "nl.overheid.zaken.zaak-verwijderd"


def send_zaak_cloudevent(event_type: str, zaak: Zaak, request: HttpRequest):
    if not settings.ENABLE_CLOUD_EVENTS:
        return

    config = CloudEventConfig.get_solo()
    if not config.enabled:
        return

    cloud_event = {
        "specversion": "1.0",
        "type": event_type,
        "source": config.source,
        "subject": str(zaak.uuid),
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": reverse("zaak-detail", kwargs={"version": "1", "uuid": zaak.uuid}),
        "datacontenttype": "application/json",
        "data": {},
    }

    send_cloud_event.delay(cloud_event)


@shared_task(bind=True)
def send_cloud_event(self, cloud_event: dict[str, Any]) -> None:
    config = CloudEventConfig.get_solo()
    if not config.enabled or not config.webhook_service:
        return

    client = build_client(config.webhook_service)
    response = client.post(
        config.webhook_path,
        json=cloud_event,
        headers={"content-type": "application/cloudevents+json"},
    )

    logger.info(
        "cloud_event_sent",
        type=cloud_event["type"],
        subject=cloud_event["subject"],
        status_code=response.status_code,
    )


class CloudEventCreateMixin:
    def perform_create(self, serializer):
        # TODO
        # with conditional_atomic(self.notifications_wrap_in_atomic_block)():
        super().perform_create(serializer)
        instance = serializer.instance
        zaak_field = getattr(self, "lookup_zaak_field", None) or "zaak"
        zaak = getattr(instance, zaak_field, None)
        send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventUpdateMixin:
    def perform_update(self, serializer):
        # with conditional_atomic(self.notifications_wrap_in_atomic_block)():
        super().perform_update(serializer)
        instance = serializer.instance
        zaak_field = getattr(self, "lookup_zaak_field", None) or "zaak"
        zaak = getattr(instance, zaak_field, None)
        send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventPostMixin:
    def perform_post(self, serializer):
        # with conditional_atomic(self.notifications_wrap_in_atomic_block)():
        super().perform_post(serializer)
        instance = serializer.instance
        zaak_field = getattr(self, "lookup_zaak_field", None) or "zaak"
        zaak = instance.get(zaak_field, None)
        send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventDestroyMixin:
    def perform_destroy(self, instance):
        # with conditional_atomic(self.notifications_wrap_in_atomic_block)():
        # get data via serializer
        zaak_field = getattr(self, "lookup_zaak_field", None) or "zaak"
        zaak = getattr(instance, zaak_field, None)
        super().perform_destroy(instance)
        send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventViewSetMixin(
    CloudEventCreateMixin, CloudEventUpdateMixin, CloudEventDestroyMixin
):
    pass
