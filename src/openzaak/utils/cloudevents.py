# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
import contextvars

from django.conf import settings
from django.db import transaction

from notifications_api_common.cloudevents import (
    process_cloudevent as _process_cloudevent,
)
from vng_api_common.tests import reverse

"""
Because cloud events are triggered via model signals, endpoints that affect multiple
resources could trigger the same cloud event twice. To avoid duplicate cloud events
within the same transaction, we keep track of a registry with scheduled event types
per object, which is reset for each request-response cycle
"""
_scheduled_events_registry = contextvars.ContextVar(
    "scheduled_events_registry", default=None
)


def get_scheduled_event_registry() -> dict[str, set[int]]:
    registry = _scheduled_events_registry.get()
    if registry is None:
        registry = {}
        _scheduled_events_registry.set(registry)
    return registry


def reset_scheduled_event_registry() -> None:
    _scheduled_events_registry.set({})


def process_cloudevent(
    type: str,
    subject: str | None = None,
    dataref: str | None = None,
    data: dict | None = None,
):
    if settings.ENABLE_CLOUD_EVENTS:
        transaction.on_commit(lambda: _process_cloudevent(type, subject, dataref, data))


def get_url(obj, request):
    if _loose_fk_data := getattr(obj, "_loose_fk_data", None):
        return _loose_fk_data["url"]

    value = reverse(obj)
    return request.build_absolute_uri(value)


class CloudEventSchedulingMiddleware:
    """
    Middleware to ensure that the cloud event scheduling registry is reset as part of
    the request-response cycle
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reset_scheduled_event_registry()
        try:
            return self.get_response(request)
        finally:
            reset_scheduled_event_registry()
