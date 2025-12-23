# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpRequest
from django.utils import timezone

import requests
from celery import shared_task
from cloudevents.http import CloudEvent
from notifications_api_common.autoretry import add_autoretry_behaviour
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse
from structlog.stdlib import get_logger
from vng_api_common.constants import ZaakobjectTypes
from zgw_consumers.client import build_client

from openzaak.components.zaken.api.serializers.zaakobjecten import ZaakObjectSerializer
from openzaak.components.zaken.models import Zaak
from openzaak.config.models import CloudEventConfig
from openzaak.notifications.viewsets import CloudEventWebhook

logger = get_logger(__name__)

ZAAK_GEOPEND = "nl.overheid.zaken.zaak-geopend"
ZAAK_GEMUTEERD = "nl.overheid.zaken.zaak-gemuteerd"
ZAAK_VERWIJDEREN = "nl.overheid.zaken.zaak-verwijderd"
ZAAK_GEKOPPELD = "nl.overheid.zaken.zaak-gekoppeld"


def _resolve_zaak_uri(uri: str) -> str | None:
    """Resolve a uri that is supposed to be a zaak and return its api url."""

    match uri.split(":"):
        case "urn", "uuid", uuid:
            try:
                zaak = Zaak.objects.get(uuid=uuid)
            except Zaak.DoesNotExist:
                return None
            # without request, returns just path; good enough for the serializer
            return zaak.get_absolute_api_url()
        case scheme, *_ if scheme in ["https", "http"]:
            return uri
        case _:
            return None


@CloudEventWebhook.register_handler
def handle_zaak_gekoppeld(event: CloudEvent):
    if event["type"] != ZAAK_GEKOPPELD:
        return

    event_data = event.get_data()
    if not event_data:
        logger.warning("incoming_cloud_event_error", code="missing-data")
        return

    if not (zaak := _resolve_zaak_uri(event_data.get("zaak", ""))):
        logger.warning("incoming_cloud_event_error", code="unknown-zaak")
        return

    object_type = (
        {"object_type": ot}
        if (ot := event_data.get("linkObjectType")) in ZaakobjectTypes
        else {"object_type": ZaakobjectTypes.overige, "object_type_overige": ot}
    )

    data = ZaakObjectSerializer(
        data={
            "zaak": zaak,
            "object": event_data.get("linkTo"),
            "relatieomschrijving": event_data.get("label"),
        }
        | object_type
    )

    try:
        data.is_valid(raise_exception=True)
        data.save()
    except (ValidationError, DatabaseError) as e:
        logger.warning("incoming_cloud_event_error", exc_info=e)


@contextmanager
def _fake_atomic():
    yield


class CloudEventException(Exception):
    pass


def conditional_atomic(wrap: bool = True):
    """
    Wrap either a fake or real atomic transaction context manager.
    """
    return transaction.atomic if wrap else _fake_atomic


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

    try:
        response = client.post(
            config.webhook_path,
            json=cloud_event,
            headers={"content-type": "application/cloudevents+json"},
        )
        response.raise_for_status()
    # any unexpected errors should show up in error-monitoring, so we only
    # catch HTTPError exceptions
    except requests.HTTPError as exc:
        logger.warning(
            "cloud_event_error",
            exc_info=exc,
            extra={
                "notification_msg": cloud_event,
                "current_try": self.request.retries + 1,
                "final_try": self.request.retries >= self.max_retries,
                "base_url": client.base_url,
            },
        )
        raise CloudEventException from exc
    else:
        logger.info(
            "cloud_event_sent",
            type=cloud_event["type"],
            subject=cloud_event["subject"],
            status_code=response.status_code,
        )


add_autoretry_behaviour(
    send_cloud_event,
    autoretry_for=(
        CloudEventException,
        requests.RequestException,
    ),
    retry_jitter=False,
)


class CloudEventMixin:
    cloud_events_wrap_in_atomic_block = True

    def _get_zaak_from_instance(self, instance):
        zaak_field = getattr(self, "lookup_zaak_field", "zaak")
        return getattr(instance, zaak_field, None)

    def _get_zaak_from_dict(self, data):
        zaak_field = getattr(self, "lookup_zaak_field", "zaak")
        return data.get(zaak_field, None)


class CloudEventCreateMixin(CloudEventMixin):
    def perform_create(self, serializer):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            super().perform_create(serializer)
            zaak = self._get_zaak_from_instance(serializer.instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventUpdateMixin(CloudEventMixin):
    def perform_update(self, serializer):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            super().perform_update(serializer)
            zaak = self._get_zaak_from_instance(serializer.instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventPostMixin(CloudEventMixin):
    def perform_post(self, serializer):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            super().perform_post(serializer)
            zaak = self._get_zaak_from_dict(serializer.instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventDestroyMixin(CloudEventMixin):
    def perform_destroy(self, instance):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            zaak = self._get_zaak_from_instance(instance)
            super().perform_destroy(instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak, self.request)


class CloudEventViewSetMixin(
    CloudEventCreateMixin, CloudEventUpdateMixin, CloudEventDestroyMixin
):
    pass
