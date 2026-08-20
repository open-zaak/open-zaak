# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_pagination import (
    BesluitPaginationTestCase as _BesluitPaginationTestCase,
)


class BesluitPaginationTestCase(_BesluitPaginationTestCase):
    NAMESPACE = "zaken"
