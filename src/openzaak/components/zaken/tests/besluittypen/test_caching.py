# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from openzaak.components.catalogi.tests.test_caching import (
    BesluitTypeCacheTests as _BesluitTypeCacheTests,
    BesluitTypeCacheTransactionTests as _BesluitTypeCacheTransactionTests,
)


class BesluitTypeCacheTests(_BesluitTypeCacheTests):
    NAMESPACE = "zaken"


class BesluitTypeCacheTransactionTests(_BesluitTypeCacheTransactionTests):
    NAMESPACE = "zaken"
