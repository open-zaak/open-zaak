# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
import logging
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.http import HttpRequest
from django.utils import timezone

from celery import shared_task
from furl import furl
from vng_api_common.tests import reverse

from openzaak.components.zaken.models import Zaak
from openzaak.config.models import CloudEventConfig

logger = logging.getLogger(__name__)


def get_headers(spec: dict, tags: str) -> dict:
    """
    Override to deal with Logius schema having no operationIds
    """
    return {}


def create_cloud_event(request: HttpRequest, zaak: Zaak) -> dict[str, Any]:
    config = CloudEventConfig.get_solo()
    base_url = furl(request.build_absolute_uri())
    return {
        "specversion": "1.0",
        "type": config.type,
        "source": f"urn:nld:oin:{config.oin}:systeem:{base_url.host}",
        "subject": zaak.identificatie,  # TODO
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": request.build_absolute_uri(reverse(zaak)),
        "datacontenttype": "application/json",
        "data": {
            "zaakId": str(zaak.uuid),
            "kenmerk": zaak.identificatie,
            "titel": zaak.zaaktype.zaaktype_omschrijving,
        },
    }


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
