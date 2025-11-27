# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from opentelemetry import metrics

meter = metrics.get_meter("openzaak.components.zaken")

# zaken
zaken_create_counter = meter.create_counter(
    "openzaak.zaken.creates",
    description="Amount of zaken created (via the API).",
    unit="1",
)
zaken_update_counter = meter.create_counter(
    "openzaak.zaken.updates",
    description="Amount of zaken updated (via the API).",
    unit="1",
)
zaken_delete_counter = meter.create_counter(
    "openzaak.zaken.deletes",
    description="Amount of zaken deleted (via the API).",
    unit="1",
)
