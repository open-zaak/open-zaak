# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from openzaak.components.besluiten.tests.test_besluit_closed_zaak import (
    BesluitClosedZaakTests as _BesluitClosedZaakTests,
)


class BesluitClosedZaakTests(_BesluitClosedZaakTests):
    NAMESPACE = "besluiten"
