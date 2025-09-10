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

from openzaak.components.zaken.models import Zaak
from openzaak.config.models import CloudEventConfig

logger = get_logger(__name__)
ZAAK_GEOPEND = "nl.overheid.zaken.zaak-geopend"
ZAAK_GEMUTEERD = "nl.overheid.zaken.zaak-gemuteerd"
ZAAK_VERWIJDERN = "nl.overheid.zaken.zaak-verwijderd"


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
    if not config.enabled or not config.logius_service:
        return

    client = config.logius_service.build_client()
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
