# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from contextlib import contextmanager

from django.db import transaction

from rest_framework.reverse import reverse
from structlog.stdlib import get_logger

from openzaak.components.zaken.models import Zaak
from openzaak.utils.cloudevents import process_cloudevent

logger = get_logger(__name__)

ZAAK_GEOPEND = "nl.overheid.zaken.zaak-geopend"
ZAAK_GEMUTEERD = "nl.overheid.zaken.zaak-gemuteerd"
ZAAK_VERWIJDEREN = "nl.overheid.zaken.zaak-verwijderd"
ZAAK_GEREGISTREERD = "nl.overheid.zaken.zaak-geregistreerd"
ZAAK_OPGESCHORT = "nl.overheid.zaken.zaak-opgeschort"
ZAAK_BIJGEWERKT = "nl.overheid.zaken.zaak-bijgewerkt"
ZAAK_VERLENGD = "nl.overheid.zaken.zaak-verlengd"
ZAAK_AFGESLOTEN = "nl.overheid.zaken.zaak-afgesloten"


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


def send_zaak_cloudevent(event_type: str, zaak: Zaak):
    process_cloudevent(
        event_type,
        str(zaak.uuid),
        reverse("zaak-detail", kwargs={"version": "1", "uuid": zaak.uuid}),
        {},
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
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak)


class CloudEventUpdateMixin(CloudEventMixin):
    def perform_update(self, serializer):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            super().perform_update(serializer)
            zaak = self._get_zaak_from_instance(serializer.instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak)


class CloudEventPostMixin(CloudEventMixin):
    def perform_post(self, serializer):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            super().perform_post(serializer)
            zaak = self._get_zaak_from_dict(serializer.instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak)


class CloudEventDestroyMixin(CloudEventMixin):
    def perform_destroy(self, instance):
        with conditional_atomic(self.cloud_events_wrap_in_atomic_block)():
            zaak = self._get_zaak_from_instance(instance)
            super().perform_destroy(instance)
            send_zaak_cloudevent(ZAAK_GEMUTEERD, zaak)


class CloudEventViewSetMixin(
    CloudEventCreateMixin, CloudEventUpdateMixin, CloudEventDestroyMixin
):
    pass
