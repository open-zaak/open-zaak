# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_besluit_read import (
    BesluitReadTests as _BesluitReadTests,
)


class BesluitReadTests(_BesluitReadTests):
    NAMESPACE = "zaken"
