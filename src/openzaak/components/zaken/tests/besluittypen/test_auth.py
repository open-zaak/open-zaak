# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_auth import (
    BesluitTypePublishedTypesForcedDeletionTests as _BesluitTypePublishedTypesForcedDeletionTests,
    BesluitTypePublishedTypesForcedWriteTests as _BesluitTypePublishedTypesForcedWriteTests,
    BesluitTypeReadTests as _BesluitTypeReadTests,
)


class BesluitTypeReadTests(_BesluitTypeReadTests):
    NAMESPACE = "zaken"


class BesluitTypePublishedTypesForcedDeletionTests(
    _BesluitTypePublishedTypesForcedDeletionTests
):
    NAMESPACE = "zaken"


class BesluitTypePublishedTypesForcedWriteTests(
    _BesluitTypePublishedTypesForcedWriteTests
):
    NAMESPACE = "zaken"
