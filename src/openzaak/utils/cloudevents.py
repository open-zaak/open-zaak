# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.conf import settings

from notifications_api_common.cloudevents import (
    process_cloudevent as _process_cloudevent,
)


def process_cloudevent(
    type: str,
    subject: str | None = None,
    dataref: str | None = None,
    data: dict | None = None,
):
    if settings.ENABLE_CLOUD_EVENTS:
        _process_cloudevent(type, subject, dataref, data)
