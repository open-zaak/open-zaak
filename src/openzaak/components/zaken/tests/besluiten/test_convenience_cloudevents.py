# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from openzaak.components.besluiten.tests.test_convenience_cloudevents import (
    BesluitConvenienceCloudEventTest as _BesluitConvenienceCloudEventTest,
)


class BesluitConvenienceCloudEventTest(_BesluitConvenienceCloudEventTest):
    NAMESPACE = "zaken"
