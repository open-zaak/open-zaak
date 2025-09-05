# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from celery import shared_task
from structlog.stdlib import get_logger

from openzaak.components.zaken.models import Zaak
from openzaak.config.models import CloudEventConfig

logger = get_logger(__name__)


def get_headers(spec: dict, tags: str) -> dict:
    return {}


def send_zaak_cloudevent(event_type: str, zaak: Zaak, request: HttpRequest):
    config = CloudEventConfig.get_solo()
    if not config.enabled or not settings.ENABLE_CLOUD_EVENTS:
        return

    cloud_event = {
        "specversion": "1.0",
        "type": event_type,
        "source": "urn:nld:oin:00000001823288444000:zakensysteem",
        "subject": str(zaak.uuid),
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": f"/api/zaken/{zaak.uuid}",
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
    with patch("zds_client.client.get_headers", get_headers):
        response = client.request(
            "/event/zaak",
            ["Events"],
            method="POST",
            json=cloud_event,
            headers={"content-type": "application/cloudevents+json"},
        )

    logger.info("Response from Logius %s", response)
