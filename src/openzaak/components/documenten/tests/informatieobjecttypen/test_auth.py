# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""

from openzaak.components.catalogi.tests.test_auth import (
    InformatieObjectTypePublishedTypesForcedDeletionTests as _InformatieObjectTypePublishedTypesForcedDeletionTests,
    InformatieObjectTypePublishedTypesForcedWriteTests as _InformatieObjectTypePublishedTypesForcedWriteTests,
    InformatieObjectTypeReadTests as _InformatieObjectTypeReadTests,
)


class InformatieObjectTypeReadTests(_InformatieObjectTypeReadTests):
    NAMESPACE = "documenten"


class InformatieObjectTypePublishedTypesForcedDeletionTests(
    _InformatieObjectTypePublishedTypesForcedDeletionTests
):
    NAMESPACE = "documenten"


class InformatieObjectTypePublishedTypesForcedWriteTests(
    _InformatieObjectTypePublishedTypesForcedWriteTests
):
    NAMESPACE = "documenten"
