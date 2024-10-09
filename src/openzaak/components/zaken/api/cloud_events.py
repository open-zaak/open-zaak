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

from openzaak.components.zaken.models import Rol
from openzaak.config.models import CloudEventConfig

logger = logging.getLogger(__name__)


def get_headers(spec: dict, tags: str) -> dict:
    """
    Override to deal with Logius schema having no operationIds
    """
    return {}


def rol_create_cloud_event(request: HttpRequest, rol: Rol) -> dict[str, Any]:
    zaak = rol.zaak
    config = CloudEventConfig.get_solo()
    base_url = furl(request.build_absolute_uri())
    return {
        "specversion": "1.0",
        "type": config.zaak_create_event_type,
        "source": f"urn:nld:oin:{rol.zaak.bronorganisatie}:systeem:{base_url.host}",
        "subject": rol.natuurlijkpersoon.inp_bsn,
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": request.build_absolute_uri(reverse(rol)),
        "datacontenttype": "application/json",
        "data": {
            "zaakId": str(zaak.uuid),
            "kenmerk": zaak.identificatie,
            "titel": zaak.zaaktype.zaaktype_omschrijving,
        },
    }


def status_create_cloud_event(request: HttpRequest, status) -> dict[str, Any]:
    zaak = status.zaak
    rol = zaak.rol_set.get(_roltype__omschrijving_generiek="initiator")
    config = CloudEventConfig.get_solo()
    base_url = furl(request.build_absolute_uri())
    return {
        "specversion": "1.0",
        "type": config.status_update_event_type,
        "source": f"urn:nld:oin:{zaak.bronorganisatie}:systeem:{base_url.host}",
        "subject": rol.natuurlijkpersoon.inp_bsn,
        "id": str(uuid4()),
        "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataref": request.build_absolute_uri(reverse(rol)),
        "datacontenttype": "application/json",
        "data": {
            "zaakId": str(zaak.uuid),
            "statustoelichting": status.statustoelichting,
            "omschrijving": status.statustype.statustype_omschrijving,
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
