# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from contextlib import contextmanager

from django.db import DatabaseError, transaction
from django.http import HttpRequest

from cloudevents.http import CloudEvent
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse
from structlog.stdlib import get_logger
from vng_api_common.constants import ZaakobjectTypes

from openzaak.components.zaken.api.serializers.zaakobjecten import ZaakObjectSerializer
from openzaak.components.zaken.models import Zaak, ZaakObject
from openzaak.notifications.viewsets import CloudEventWebhook
from openzaak.utils.cloudevents import process_cloudevent

logger = get_logger(__name__)

ZAAK_GEOPEND = "nl.overheid.zaken.zaak-geopend"
ZAAK_GEMUTEERD = "nl.overheid.zaken.zaak-gemuteerd"
ZAAK_VERWIJDEREN = "nl.overheid.zaken.zaak-verwijderd"
ZAAK_GEKOPPELD = "nl.overheid.zaken.zaak-gekoppeld"
ZAAK_ONTKOPPELD = "nl.overheid.zaken.zaak-ontkoppeld"
ZAAK_GEREGISTREERD = "nl.overheid.zaken.zaak-geregistreerd"
ZAAK_OPGESCHORT = "nl.overheid.zaken.zaak-opgeschort"
ZAAK_BIJGEWERKT = "nl.overheid.zaken.zaak-bijgewerkt"
ZAAK_VERLENGD = "nl.overheid.zaken.zaak-verlengd"
ZAAK_AFGESLOTEN = "nl.overheid.zaken.zaak-afgesloten"


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


def _resolve_zaak(uri: str) -> Zaak | None:
    """Resolve a uri that is supposed to be a zaak and return the Zaak instance."""
    match uri.split(":"):
        case "urn", "uuid", uuid:
            return Zaak.objects.filter(uuid=uuid).first()
        case scheme, *_ if scheme in ["https", "http"]:
            uuid = uri.rstrip("/").split("/")[-1]
            return Zaak.objects.filter(uuid=uuid).first()
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
        logger.info("incoming_cloud_event_handled", created=data)
    except (ValidationError, DatabaseError) as e:
        logger.warning("incoming_cloud_event_error", exc_info=e)


@CloudEventWebhook.register_handler
def handle_zaak_ontkoppeld(event: CloudEvent):
    if event["type"] != ZAAK_ONTKOPPELD:
        return

    event_data = event.get_data()
    if not event_data:
        logger.warning("incoming_cloud_event_error", code="missing-data")
        return

    if not (zaak := _resolve_zaak(event_data.get("zaak", ""))):
        logger.warning("incoming_cloud_event_error", code="unknown-zaak")
        return

    link_to = event_data.get("linkTo")
    if not link_to:
        logger.warning("incoming_cloud_event_error", code="missing-linkTo")
        return

    try:
        deleted, _ = ZaakObject.objects.filter(
            zaak=zaak,
            object=link_to,
        ).delete()

        logger.info(
            "incoming_cloud_event_handled",
            code="zaak-ontkoppeld",
            deleted=deleted,
        )

    except DatabaseError as e:
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
    data = {}
    if event_type in (ZAAK_GEOPEND, ZAAK_GEMUTEERD, ZAAK_VERWIJDEREN):
        data = {
            "bronorganisatie": zaak.bronorganisatie,
            "zaaktype": reverse(
                "zaaktype-detail",
                kwargs={"uuid": zaak.zaaktype.uuid},
                request=request,
            ),
            "zaaktype.catalogus": reverse(
                "catalogus-detail",
                kwargs={"uuid": zaak.zaaktype.catalogus.uuid},
                request=request,
            ),
            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
        }

    process_cloudevent(
        event_type,
        str(zaak.uuid),
        reverse("zaak-detail", kwargs={"version": "1", "uuid": zaak.uuid}),
        data,
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
