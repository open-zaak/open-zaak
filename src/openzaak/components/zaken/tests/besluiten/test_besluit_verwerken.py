# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from openzaak.components.besluiten.tests.test_besluit_verwerken import (
    BesluitVerwerkenAuthTests as _BesluitVerwerkenAuthTests,
    BesluitVerwerkenValidationTests as _BesluitVerwerkenValidationTests,
)


class BesluitVerwerkenAuthTests(_BesluitVerwerkenAuthTests):
    NAMESPACE = "zaken"


class BesluitVerwerkenValidationTests(_BesluitVerwerkenValidationTests):
    NAMESPACE = "zaken"
