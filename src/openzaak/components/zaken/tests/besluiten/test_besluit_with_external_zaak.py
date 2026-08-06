# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_besluit_with_external_zaak import (
    BesluitCreateExternalZaakTests as _BesluitCreateExternalZaakTests,
)


class BesluitCreateExternalZaakTests(_BesluitCreateExternalZaakTests):
    NAMESPACE = "zaken"
