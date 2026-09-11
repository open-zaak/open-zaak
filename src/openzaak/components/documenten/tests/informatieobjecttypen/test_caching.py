# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Test that the caching mechanisms are in place.
"""

from openzaak.components.catalogi.tests.test_caching import (
    InformatieObjectTypeCacheTests as _InformatieObjectTypeCacheTests,
    InformatieObjectTypeCacheTransactionTests as _InformatieObjectTypeCacheTransactionTests,
)


class InformatieObjectTypeCacheTests(_InformatieObjectTypeCacheTests):
    NAMESAPCE = "documenten"


class InformatieObjectTypeCacheTransactionTests(
    _InformatieObjectTypeCacheTransactionTests
):
    NAMESPACE = "documenten"
