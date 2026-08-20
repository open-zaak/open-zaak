# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_besluit_delete import (
    BesluitDeleteTestCase as _BesluitDeleteTestCase,
)


class BesluitDeleteTestCase(_BesluitDeleteTestCase):
    NAMESPACE = "zaken"
