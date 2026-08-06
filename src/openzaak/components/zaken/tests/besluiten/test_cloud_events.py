# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_cloud_events import (
    BesluitCloudEventTests as _BesluitCloudEventTests,
)


class BesluitCloudEventTests(_BesluitCloudEventTests):
    NAMESPACE = "zaken"
