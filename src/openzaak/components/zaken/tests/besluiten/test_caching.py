# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from openzaak.components.besluiten.tests.test_caching import (
    BesluitCacheTests as _BesluitCacheTests,
    BesluitInformatieObjectCacheTests as _BesluitInformatieObjectCacheTests,
)


class BesluitCacheTests(_BesluitCacheTests):
    NAMESPACE = "zaken"


class BesluitInformatieObjectCacheTests(_BesluitInformatieObjectCacheTests):
    NAMESPACE = "zaken"
