# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.conf import settings

from notifications_api_common.cloudevents import (
    process_cloudevent as _process_cloudevent,
)
from vng_api_common.tests import reverse


def process_cloudevent(
    type: str,
    subject: str | None = None,
    dataref: str | None = None,
    data: dict | None = None,
):
    if settings.ENABLE_CLOUD_EVENTS:
        _process_cloudevent(type, subject, dataref, data)


def get_url(obj, request):
    if _loose_fk_data := getattr(obj, "_loose_fk_data", None):
        return _loose_fk_data["url"]

    value = reverse(obj)
    return request.build_absolute_uri(value)
