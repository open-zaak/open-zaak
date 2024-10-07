# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
import logging
from unittest.mock import patch
from uuid import uuid4

from django.utils import timezone

from celery import shared_task

from openzaak.config.models import CloudEventConfig

logger = logging.getLogger(__name__)


def get_headers(spec: dict, tags: str) -> dict:
    """
    Override to deal with Logius schema having no operationIds
    """
    return {}


@shared_task(bind=True)
def send_cloud_event(self, host: str, zaak_data: dict) -> None:
    config = CloudEventConfig.get_solo()
    if not config.enabled or not config.logius_service:
        return

    data = {
        "specversion": "1.0",
        "type": config.type,
        "source": f"urn:nld:oin:{config.oin}:systeem:{host}",
        "subject": zaak_data["identificatie"],  # TODO
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": zaak_data["url"],
        "datacontenttype": "application/json",
        "data": {
            "zaakId": zaak_data["uuid"],  # TODO or identificatie?
            # "kenmerk": zaak_data["kenmerken"][0] if zaak_data["kenmerken"] else "",
            "kenmerk": zaak_data["omschrijving"],
            "titel": zaak_data["omschrijving"],
        },
    }

    client = config.logius_service.build_client()
    with patch("zds_client.client.get_headers", get_headers):
        response = client.request(
            "/event/zaak",
            ["Events"],
            method="POST",
            json=data,
            headers={"content-type": "application/cloudevents+json"},
        )

    logger.info("Response from Logius %s", response)
