# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_auth import (
    PublishedTypesForcedDeletionTests as _PublishedTypesForcedDeletionTests,
    PublishedTypesForcedWriteTests as _PublishedTypesForcedWriteTests,
    ZaakTypeReadTests as _ZaakTypeReadTests,
)


class ZaakTypeReadTests(_ZaakTypeReadTests):
    NAMESPACE = "zaken"


class PublishedTypesForcedDeletionTests(_PublishedTypesForcedDeletionTests):
    NAMESPACE = "zaken"


class PublishedTypesForcedWriteTests(_PublishedTypesForcedWriteTests):
    NAMESPACE = "zaken"
